import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from teapass.models import Batch
from teapass.security import command_bytes
from teapass.workflow_models import AccessLog, Custody, PermissionGrant
from teapass.workflow_schemas import workflow_adapter


def encrypted():
    return dict(
        algorithm="A256GCM",
        key_id=str(uuid4()),
        nonce=base64.b64encode(b"n" * 12).decode(),
        ciphertext=base64.b64encode(b"c" * 32).decode(),
    )


def signed(env, recorded, kind, name="grower", **fields):
    batch, previous = recorded
    actor = env.identities[name].actor
    payload = dict(
        schema_version="1.0",
        deployment_id=env.settings.deployment_id,
        actor_id=str(actor.id),
        org_id=str(actor.org_id),
        operation_id=str(uuid4()),
        batch_id=batch["command"]["batch_id"],
        occurred_at=datetime.now(UTC).isoformat(),
        command_type=kind,
        previous_event_hash=previous["event_hash"],
        **fields,
    )
    c = workflow_adapter.validate_python(payload)
    return dict(
        command=c.model_dump(mode="json"),
        signature=base64.b64encode(env.identities[name].key.sign(command_bytes(c))).decode(),
    )


def post(env, body, name="grower", key=None):
    return env.client.post(
        "/v1/workflows", json=body, headers=env.headers(name, key or uuid4().hex)
    )


def grant(env, recorded, recipient="auditor", scope="events"):
    body = signed(
        env,
        recorded,
        "GRANT_EVIDENCE",
        grant_id=str(uuid4()),
        recipient_id=str(env.identities[recipient].actor.id),
        scope=scope,
        expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        key_envelope=dict(
            algorithm="X25519-HKDF-SHA256-A256GCM",
            key_id=str(uuid4()),
            ephemeral_public_key=base64.b64encode(b"p" * 32).decode(),
            nonce=base64.b64encode(b"n" * 12).decode(),
            ciphertext=base64.b64encode(b"c" * 48).decode(),
        ),
    )
    response = post(env, body)
    assert response.status_code == 201, response.text
    return body, response.json()


def offer(env, recorded):
    body = signed(
        env,
        recorded,
        "OFFER_CUSTODY",
        transfer_id=str(uuid4()),
        receiver_id=str(env.identities["other"].actor.id),
        expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        note_commitment="a" * 64,
    )
    response = post(env, body)
    assert response.status_code == 201, response.text
    return body, response.json()


def test_custody_dual_signature_idempotency_and_tenant_boundary(env, recorded):
    body, result = offer(env, recorded)
    transfer_id = body["command"]["transfer_id"]
    path = "/v1/custody/" + transfer_id
    assert env.client.get(path, headers=env.headers("buyer")).status_code == 404
    response = signed(
        env,
        (recorded[0], result),
        "RESPOND_CUSTODY",
        name="other",
        transfer_id=transfer_id,
        offer_event_hash=result["event_hash"],
        decision="ACCEPTED",
    )
    accepted = post(env, response, "other", "custody-accept-1")
    assert accepted.status_code == 201, accepted.text
    assert post(env, response, "other", "custody-accept-1").json() == accepted.json()
    assert post(env, response, "other").status_code == 409
    detail = env.client.get(path, headers=env.headers("other")).json()
    assert (
        detail["status"] == "ACCEPTED" and detail["response"]["signature"] == response["signature"]
    )
    with env.app.state.sessions() as db:
        assert (
            db.get(Batch, UUID(recorded[0]["command"]["batch_id"])).org_id
            == env.identities["grower"].actor.org_id
        )


@pytest.mark.parametrize("alteration", ["wrong-offer", "tampered", "wrong-receiver", "expired"])
def test_custody_rejects_unbound_or_unauthorized_response(env, recorded, alteration):
    body, result = offer(env, recorded)
    if alteration == "expired":
        with env.app.state.sessions() as db, db.begin():
            db.get(Custody, UUID(body["command"]["transfer_id"])).expires_at = datetime.now(
                UTC
            ) - timedelta(seconds=1)
    name = "buyer" if alteration == "wrong-receiver" else "other"
    response = signed(
        env,
        (recorded[0], result),
        "RESPOND_CUSTODY",
        name=name,
        transfer_id=body["command"]["transfer_id"],
        decision="DISCREPANCY",
        offer_event_hash="b" * 64 if alteration == "wrong-offer" else result["event_hash"],
    )
    if alteration == "tampered":
        response["command"]["decision"] = "ACCEPTED"
    assert post(env, response, name).status_code in {403, 404, 409, 422}


def test_only_one_custody_offer_wins_concurrent_requests(env, recorded):
    def make():
        return signed(
            env,
            recorded,
            "OFFER_CUSTODY",
            transfer_id=str(uuid4()),
            receiver_id=str(env.identities["other"].actor.id),
            note_commitment="a" * 64,
            expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        )

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda body: post(env, body).status_code, [make(), make()]))
    assert sorted(results) == [201, 409]


def test_auditor_scoped_access_logged_and_revoked(env, recorded):
    body, result = grant(env, recorded)
    path = "/v1/audit/grants/" + body["command"]["grant_id"] + "/events"
    assert env.client.get(path, headers=env.headers("other")).status_code == 404
    audit = env.client.get(path, headers=env.headers("auditor"))
    assert audit.status_code == 200 and len(audit.json()["events"]) == 2
    with env.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(AccessLog)) == 1
    revoke = signed(
        env, (recorded[0], result), "REVOKE_GRANT", grant_id=body["command"]["grant_id"]
    )
    assert post(env, revoke).status_code == 201
    assert env.client.get(path, headers=env.headers("auditor")).status_code == 404


def test_expired_grant_denies_existing_auditor(env, recorded):
    body, _ = grant(env, recorded)
    with env.app.state.sessions() as db, db.begin():
        db.get(PermissionGrant, UUID(body["command"]["grant_id"])).expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)
    path = "/v1/audit/grants/" + body["command"]["grant_id"] + "/events"
    assert env.client.get(path, headers=env.headers("auditor")).status_code == 404


def test_lab_requires_explicit_scoped_grant_and_never_claims_verified(env, recorded):
    fields = dict(
        attestation_id=str(uuid4()),
        commitment="c" * 64,
        policy_id="d" * 64,
        expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        encrypted_payload=encrypted(),
    )
    body = signed(env, recorded, "ATTEST_LAB", name="lab", **fields)
    assert post(env, body, "lab").status_code == 403
    _, result = grant(env, recorded, "lab", "lab_attest")
    body = signed(env, (recorded[0], result), "ATTEST_LAB", name="lab", **fields)
    assert post(env, body, "lab").status_code == 201
    public = env.client.get("/v1/public/batches/" + recorded[0]["command"]["public_alias"]).json()
    assert public["claims"] == [] and public["verification_status"] == "NOT_VERIFIED"
    assert "ciphertext" not in str(public) and fields["commitment"] not in str(public)


def test_chain_jobs_fail_closed_without_network_configuration(env, recorded):
    body = signed(
        env,
        recorded,
        "PREPARE_CHAIN",
        job_id=str(uuid4()),
        operation="issue",
        output_commitments=["a" * 64],
        encrypted_payload=encrypted(),
    )
    assert post(env, body).status_code == 503


def test_chain_intent_and_submission_remain_pending_until_reconciliation(env, recorded):
    env.settings.midnight_contract_address = "f" * 64
    body = signed(
        env,
        recorded,
        "PREPARE_CHAIN",
        job_id=str(uuid4()),
        operation="issue",
        output_commitments=["a" * 64],
        encrypted_payload=encrypted(),
    )
    prepared = post(env, body)
    assert prepared.status_code == 201, prepared.text
    job_id = body["command"]["job_id"]
    submitted = signed(
        env, (recorded[0], prepared.json()), "SUBMIT_CHAIN", job_id=job_id, tx_id="e" * 64
    )
    assert post(env, submitted).status_code == 201
    status = env.client.get("/v1/transactions/" + job_id, headers=env.headers()).json()
    assert status["status"] == "SUBMITTED" and status["receipt"] is None
    assert (
        env.client.get("/v1/transactions/" + job_id, headers=env.headers("other")).status_code
        == 404
    )
    assert (
        env.client.get("/v1/transactions/" + job_id, headers=env.headers("buyer")).status_code
        == 403
    )


def test_lab_can_track_its_own_anchor_job_only_with_explicit_batch_grant(env, recorded):
    env.settings.midnight_contract_address = "f" * 64
    _, result = grant(env, recorded, "lab", "lab_attest")
    body = signed(
        env,
        (recorded[0], result),
        "PREPARE_CHAIN",
        name="lab",
        job_id=str(uuid4()),
        operation="anchorLab",
        output_commitments=["e" * 64],
        encrypted_payload=encrypted(),
    )
    prepared = post(env, body, "lab")
    assert prepared.status_code == 201, prepared.text
    submitted = signed(
        env,
        (recorded[0], prepared.json()),
        "SUBMIT_CHAIN",
        name="lab",
        job_id=body["command"]["job_id"],
        tx_id="c" * 64,
    )
    assert post(env, submitted, "lab").status_code == 201
    result = env.client.get(
        "/v1/transactions/" + body["command"]["job_id"], headers=env.headers("lab")
    )
    assert result.status_code == 200 and result.json()["status"] == "SUBMITTED"
