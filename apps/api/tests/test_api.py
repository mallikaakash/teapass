import base64
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from teapass.models import Actor, BatchEvent, Organization
from teapass.security import digest


def make_event(env, body, result, **overrides):
    command = body["command"]
    fields = {
        key: command[key]
        for key in [
            "schema_version",
            "deployment_id",
            "actor_id",
            "org_id",
            "batch_id",
            "occurred_at",
        ]
    }
    fields.update(
        command_type="APPEND_EVENT",
        operation_id=str(uuid4()),
        event_type="OBSERVATION_RECORDED",
        previous_event_hash=result["event_hash"],
    )
    fields.update(overrides)
    return env.signed(fields)


def test_health_and_migrations(env):
    assert env.client.get("/health/live").json() == {"status": "ok"}
    assert env.client.get("/health/ready").json() == {"status": "ok", "chain": "unavailable"}


def test_authentication_required(env):
    assert env.client.get("/v1/me").status_code == 401
    assert env.client.get("/v1/me", headers=env.headers()).json()["role"] == "grower"


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "wrong"},
        {"iss": "https://forged.example"},
        {"exp": 1},
        {"iat": 1, "exp": 9999999999},
        {"sub": "unknown"},
    ],
)
def test_invalid_auth_claims(env, claims):
    assert env.client.get("/v1/me", headers=env.headers(**claims)).status_code in {401, 403}


def test_role_claim_cannot_escalate(env):
    result = env.client.post(
        "/v1/actors",
        headers=env.headers(roles=["admin"]),
        json={
            "subject": "intruder",
            "role": "grower",
            "signing_public_key": base64.b64encode(b"x" * 32).decode(),
        },
    )
    assert result.status_code == 403


@pytest.mark.parametrize("target", ["actor", "organization"])
def test_revocation_is_immediate(env, target):
    token = env.headers()
    identity = env.identities["grower"].actor
    with env.app.state.sessions() as db, db.begin():
        record = (
            db.get(Actor, identity.id)
            if target == "actor"
            else db.get(Organization, identity.org_id)
        )
        record.active = False
    assert env.client.get("/v1/me", headers=token).status_code == 403


def test_signed_creation_retry_and_key_conflict(env, recorded):
    body, result = recorded
    response = env.client.post("/v1/batches", json=body, headers=env.headers())
    assert response.status_code == 201
    assert response.json() == result
    changed = env.batch(public_alias="CHANGED-ALIAS")
    assert env.client.post("/v1/batches", json=changed, headers=env.headers()).status_code == 409
    with env.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(BatchEvent)) == 1


def test_concurrent_retry_creates_one_event(env):
    body = env.batch()

    def send(_):
        return env.client.post("/v1/batches", json=body, headers=env.headers())

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(send, range(6)))
    assert [r.status_code for r in results] == [201] * 6
    assert len({r.json()["event_hash"] for r in results}) == 1
    with env.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(BatchEvent)) == 1


def test_tampering_and_cross_deployment_rejected(env):
    body = env.batch()
    body["command"]["public_alias"] = "TAMPERED-ALIAS"
    assert env.client.post("/v1/batches", json=body, headers=env.headers()).status_code == 403
    body = env.batch(deployment_id="other-deployment")
    assert env.client.post("/v1/batches", json=body, headers=env.headers()).status_code == 403


def test_actor_binding(env):
    body = env.batch()
    assert (
        env.client.post("/v1/batches", json=body, headers=env.headers("other")).status_code == 403
    )


def test_unknown_fields_and_validation_do_not_echo_secrets(env):
    body = env.batch()
    body["command"]["recipe"] = "SUPER-SECRET-RECIPE"
    response = env.client.post("/v1/batches", json=body, headers=env.headers())
    assert response.status_code == 422
    assert "SUPER-SECRET" not in response.text


def test_public_projection_and_publication_consent(env, recorded):
    body, _ = recorded
    response = env.client.get("/v1/public/batches/" + body["command"]["public_alias"])
    assert response.status_code == 200
    result = response.json()
    assert result["verification_status"] == "NOT_VERIFIED"
    assert result["claims"] == [] and result["chain_receipt"] is None
    for private in [
        "PRIVATE-SUPPLIER-001",
        body["command"]["actor_id"],
        body["command"]["org_id"],
        body["signature"],
    ]:
        assert private not in response.text
    assert response.headers["cache-control"] == "no-store"
    private = env.batch(external_id="private-002", published=False)
    assert (
        env.client.post(
            "/v1/batches", json=private, headers=env.headers(key="private-002")
        ).status_code
        == 201
    )
    assert (
        env.client.get("/v1/public/batches/" + private["command"]["public_alias"]).status_code
        == 404
    )


@pytest.mark.parametrize(
    "role,expected", [("other", 404), ("buyer", 403), ("lab", 403), ("auditor", 403)]
)
def test_private_isolation(env, recorded, role, expected):
    _, result = recorded
    for resource in ["events", "lineage"]:
        response = env.client.get(
            f"/v1/private/batches/{result['batch_id']}/{resource}", headers=env.headers(role)
        )
        assert response.status_code == expected


def test_event_chain_and_stale_parent(env, recorded):
    body, result = recorded
    event = make_event(env, body, result)
    url = f"/v1/batches/{result['batch_id']}/events"
    response = env.client.post(url, json=event, headers=env.headers(key="append-001"))
    assert response.status_code == 201, response.text
    assert response.json()["sequence"] == 2
    stale = make_event(env, body, result)
    assert (
        env.client.post(url, json=stale, headers=env.headers(key="append-002")).status_code == 409
    )
    events = env.client.get(
        f"/v1/private/batches/{result['batch_id']}/events", headers=env.headers()
    ).json()["events"]
    assert events[1]["previous_event_hash"] == events[0]["event_hash"]
    for item in events:
        assert item["event_hash"] == digest(
            {
                "domain": "TEAPASS_EVENT_V1",
                "command": item["command"],
                "signature": item["signature"],
                "previous_event_hash": item["previous_event_hash"],
                "sequence": item["sequence"],
            }
        )


def test_concurrent_appends_cannot_fork_history(env, recorded):
    body, result = recorded
    url = f"/v1/batches/{result['batch_id']}/events"
    events = [make_event(env, body, result) for _ in range(2)]

    def send(i):
        return env.client.post(url, json=events[i], headers=env.headers(key=f"concurrent-{i}"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, range(2)))
    assert sorted(r.status_code for r in responses) == [201, 409]


@pytest.mark.parametrize(
    "mutation",
    ["UPDATE batch_events SET sequence = 900", "DELETE FROM batch_events", "TRUNCATE batch_events"],
)
def test_database_prevents_history_mutation(env, recorded, mutation):
    with pytest.raises(DBAPIError), env.app.state.sessions() as db, db.begin():
        db.execute(text(mutation))


def test_operation_id_replay_with_new_key_rejected(env, recorded):
    body, _ = recorded
    response = env.client.post("/v1/batches", json=body, headers=env.headers(key="replayed-001"))
    assert response.status_code == 409


def test_opaque_encrypted_payload_stays_private(env):
    secret = base64.b64encode(b"synthetic-ciphertext" * 4).decode()
    body = env.batch(
        encrypted_payload={
            "algorithm": "A256GCM",
            "key_id": str(uuid4()),
            "nonce": base64.b64encode(b"n" * 12).decode(),
            "ciphertext": secret,
        }
    )
    response = env.client.post("/v1/batches", json=body, headers=env.headers())
    assert response.status_code == 201
    public = env.client.get("/v1/public/batches/" + body["command"]["public_alias"])
    assert secret not in public.text
    events = env.client.get(
        f"/v1/private/batches/{response.json()['batch_id']}/events", headers=env.headers()
    )
    assert secret in events.text


def test_payload_size_limit(env):
    response = env.client.post("/v1/batches", content=b"x" * 131073, headers=env.headers())
    assert response.status_code == 413


def test_chain_cannot_be_faked(env):
    response = env.client.post(
        "/v1/issuances/submit", json={"verified": True}, headers=env.headers()
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_admin_enrollment_is_tenant_bound_and_idempotent(env):
    body = {
        "subject": "new-grower",
        "role": "grower",
        "signing_public_key": base64.b64encode(b"x" * 32).decode(),
    }
    response = env.client.post("/v1/actors", json=body, headers=env.headers("admin"))
    assert response.status_code == 201
    assert response.json()["org_id"] == str(env.identities["admin"].actor.org_id)
    assert (
        env.client.post("/v1/actors", json=body, headers=env.headers("admin")).json()
        == response.json()
    )
    body["role"] = "admin"
    assert env.client.post("/v1/actors", json=body, headers=env.headers("admin")).status_code == 422


def test_correction_requires_existing_event(env, recorded):
    body, result = recorded
    event = make_event(env, body, result, event_type="CORRECTION_RECORDED")
    url = f"/v1/batches/{result['batch_id']}/events"
    assert (
        env.client.post(url, json=event, headers=env.headers(key="correction-1")).status_code == 422
    )
    event = make_event(
        env, body, result, event_type="CORRECTION_RECORDED", supersedes_event_id=result["event_id"]
    )
    assert (
        env.client.post(url, json=event, headers=env.headers(key="correction-1")).status_code == 201
    )
