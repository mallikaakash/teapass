"""Receipt reconciliation against the configured indexer AND node finalized chain.

This confirms inclusion, not that a client's declared metadata matches private circuit inputs.
No client or admin API can set a finalized status. Rechecks fail closed on node/indexer outages.
"""

import argparse
import time
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import or_, select

from teapass.config import Settings
from teapass.db import make_database
from teapass.workflow_models import ChainJob

TX_QUERY = """query Receipt($offset: TransactionOffset!) {
  transactions(offset: $offset) {
    hash protocolVersion contractActions { address }
    block { height hash }
    ... on RegularTransaction { identifiers transactionResult { status } }
  }
}"""


class ObservationUnavailable(Exception):
    pass


def rpc(client, url, method, params):
    response = client.post(
        url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    )
    response.raise_for_status()
    result = response.json()
    if result.get("error") or result.get("result") is None:
        raise ObservationUnavailable()
    return result["result"]


def observe(client, settings, job):
    response = client.post(
        settings.midnight_indexer_url,
        json={"query": TX_QUERY, "variables": {"offset": {"identifier": job.tx_id}}},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise ObservationUnavailable()
    matches = [
        tx for tx in payload["data"]["transactions"] if job.tx_id in tx.get("identifiers", [])
    ]
    if not matches:
        return "SUBMITTED", None
    if len(matches) != 1:
        raise ObservationUnavailable()
    tx = matches[0]
    if job.contract_address not in {a["address"] for a in tx["contractActions"]}:
        return "REJECTED_BINDING", None
    height = tx["block"]["height"]
    if type(height) is not int or height < 0:
        raise ObservationUnavailable()
    finalized = rpc(client, settings.midnight_node_url, "chain_getFinalizedHead", [])
    header = rpc(client, settings.midnight_node_url, "chain_getHeader", [finalized])
    if int(header["number"], 16) < height:
        return "INCLUDED", None
    canonical = rpc(client, settings.midnight_node_url, "chain_getBlockHash", [height])
    if canonical.removeprefix("0x") != tx["block"]["hash"].removeprefix("0x"):
        return "REORGED", None
    status = tx["transactionResult"]["status"]
    # Indexer 4.3.5 uses SUCCESS; never accept partial success for atomic inventory.
    if status != "SUCCESS":
        return "REJECTED_CHAIN", None
    return "FINALIZED", {
        "tx_id": job.tx_id,
        "tx_hash": tx["hash"],
        "block_height": height,
        "block_hash": tx["block"]["hash"],
        "contract_address": job.contract_address,
        "network": job.network,
        "protocol_version": tx["protocolVersion"],
        "verification": "RECEIPT_INCLUSION_ONLY",
    }


def reconcile_once(settings, *, client=None):
    if not settings.midnight_contract_address:
        raise RuntimeError("Configure a pinned Midnight contract before running reconciliation")
    engine, sessions = make_database(settings)
    owned_client = client is None
    client = client or httpx.Client(timeout=5, follow_redirects=False)
    checked = 0
    try:
        with sessions() as db, db.begin():
            jobs = db.scalars(
                select(ChainJob)
                .where(
                    ChainJob.tx_id.is_not(None),
                    ChainJob.network == settings.midnight_network,
                    ChainJob.contract_address == settings.midnight_contract_address,
                    or_(
                        ChainJob.last_checked_at.is_(None),
                        ChainJob.last_checked_at < datetime.now(UTC) - timedelta(seconds=30),
                    ),
                )
                .order_by(ChainJob.last_checked_at.asc().nullsfirst())
                .limit(25)
                .with_for_update(skip_locked=True)
            ).all()
            for job in jobs:
                try:
                    job.status, job.receipt = observe(client, settings, job)
                except (httpx.HTTPError, ObservationUnavailable, KeyError, ValueError, TypeError):
                    job.status, job.receipt = "RECHECK_REQUIRED", None
                job.last_checked_at = datetime.now(UTC)
                checked += 1
    finally:
        if owned_client:
            client.close()
        engine.dispose()
    return checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    while True:
        print(f"Reconciled {reconcile_once(settings)} transaction records", flush=True)
        if args.once:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
