from types import SimpleNamespace

import httpx
import pytest

from teapass.epcis import export_document
from teapass.reconcile import observe


def test_epcis_signed_round_trip_is_idempotent(env, recorded):
    path = "/v1/integrations/epcis/export/" + recorded[0]["command"]["batch_id"]
    response = env.client.get(path, headers=env.headers())
    assert response.status_code == 200
    document = response.json()
    assert document["epcisBody"]["eventList"][0]["teapass:signed"] == recorded[0]
    imported = env.client.post(
        "/v1/integrations/epcis/import", json=document, headers=env.headers(key="epcis-import-1")
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["events"][0]["status"] == "ALREADY_RECORDED"
    assert (
        env.client.post(
            "/v1/integrations/epcis/import",
            json=document,
            headers=env.headers(key="epcis-import-1"),
        ).json()
        == imported.json()
    )
    assert env.client.get(path, headers=env.headers("buyer")).status_code == 403
    assert env.client.get(path, headers=env.headers("other")).status_code == 404


@pytest.mark.parametrize(
    "alteration", ["batch", "time", "context", "signature", "unknown", "quantity"]
)
def test_epcis_rejects_changed_bindings_and_unsupported_data(env, recorded, alteration):
    document = env.client.get(
        "/v1/integrations/epcis/export/" + recorded[0]["command"]["batch_id"], headers=env.headers()
    ).json()
    event = document["epcisBody"]["eventList"][0]
    if alteration == "batch":
        event["epcList"] = ["urn:uuid:wrong"]
    elif alteration == "time":
        event["eventTime"] = "2000-01-01T00:00:00Z"
    elif alteration == "context":
        document["@context"] = ["http://127.0.0.1/private"]
    elif alteration == "signature":
        event["teapass:signed"]["signature"] = "x" * 88
    elif alteration == "quantity":
        event["quantityList"] = [{"quantity": 100}]
    else:
        document["teapass:unrecognized"] = True
    response = env.client.post(
        "/v1/integrations/epcis/import", json=document, headers=env.headers(key="import-negative")
    )
    assert response.status_code in {403, 422}


def test_epcis_creates_signed_records_atomically(env):
    body = env.batch()
    event = SimpleNamespace(
        signed_command=body["command"],
        signature=body["signature"],
        id=body["command"]["operation_id"],
        batch_id=body["command"]["batch_id"],
    )
    document = export_document([event])
    good = env.client.post(
        "/v1/integrations/epcis/import", json=document, headers=env.headers(key="new-import")
    )
    assert good.status_code == 200, good.text
    assert good.json()["events"][0]["sequence"] == 1


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("final", "FINALIZED"),
        ("pending", "SUBMITTED"),
        ("wrong-contract", "REJECTED_BINDING"),
        ("unfinalized", "INCLUDED"),
        ("reorg", "REORGED"),
        ("failed", "REJECTED_CHAIN"),
        ("partial", "REJECTED_CHAIN"),
    ],
)
def test_reconciler_never_promotes_unconfirmed_failed_or_unbound_receipts(scenario, expected):
    txid, address, block = "a" * 64, "b" * 64, "c" * 64
    settings = SimpleNamespace(
        midnight_indexer_url="https://indexer.example/graphql",
        midnight_node_url="https://node.example",
    )
    job = SimpleNamespace(tx_id=txid, contract_address=address, network="undeployed")
    tx = {
        "hash": "d" * 64,
        "protocolVersion": 1000300,
        "identifiers": [txid],
        "contractActions": [{"address": address}],
        "block": {"height": 10, "hash": block},
        "transactionResult": {"status": "SUCCESS"},
    }
    if scenario == "wrong-contract":
        tx["contractActions"][0]["address"] = "e" * 64
    if scenario in {"failed", "partial"}:
        tx["transactionResult"]["status"] = "FAILURE" if scenario == "failed" else "PARTIAL_SUCCESS"

    def handler(request):
        import json

        body = json.loads(request.content)
        if "query" in body:
            return httpx.Response(
                200, json={"data": {"transactions": [] if scenario == "pending" else [tx]}}
            )
        if body["method"] == "chain_getFinalizedHead":
            return httpx.Response(200, json={"result": "0x" + block})
        if body["method"] == "chain_getHeader":
            return httpx.Response(
                200, json={"result": {"number": "0x09" if scenario == "unfinalized" else "0x20"}}
            )
        return httpx.Response(
            200, json={"result": "0x" + ("e" * 64 if scenario == "reorg" else block)}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        status, receipt = observe(client, settings, job)
    assert status == expected
    assert (receipt is not None) == (expected == "FINALIZED")
