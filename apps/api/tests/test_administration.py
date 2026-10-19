import base64
from datetime import UTC, datetime
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select

from teapass.administration import ActorCommand
from teapass.models import BatchEvent
from teapass.security import command_bytes
from teapass.workflow_models import AdministrationEvent


def command(env, action, name="admin", target="grower", **fields):
    a = env.identities[name].actor
    c = ActorCommand(
        schema_version="1.0",
        deployment_id=env.settings.deployment_id,
        actor_id=a.id,
        org_id=a.org_id,
        operation_id=uuid4(),
        occurred_at=datetime.now(UTC),
        command_type="MANAGE_ACTOR",
        target_id=env.identities[target].actor.id,
        action=action,
        **fields,
    )
    return c, {
        "command": c.model_dump(mode="json"),
        "signature": base64.b64encode(env.identities[name].key.sign(command_bytes(c))).decode(),
    }


def test_deactivation_denies_preexisting_access_tokens(env, recorded):
    _, body = command(env, "SET_ACTIVE", active=False)
    result = env.client.post("/v1/actors/lifecycle", json=body, headers=env.headers("admin"))
    assert result.status_code == 200, result.text
    assert env.client.get("/v1/me", headers=env.headers()).status_code == 403
    with env.app.state.sessions() as db:
        assert db.scalar(select(AdministrationEvent)).action == "SET_ACTIVE"


def test_rotation_requires_new_key_possession_and_preserves_historical_key(env, recorded):
    new_key = Ed25519PrivateKey.generate()
    old_public = env.identities["grower"].key.public_key().public_bytes_raw()
    c, body = command(
        env,
        "ROTATE_KEY",
        new_public_key=base64.b64encode(new_key.public_key().public_bytes_raw()).decode(),
    )
    assert (
        env.client.post("/v1/actors/lifecycle", json=body, headers=env.headers("admin")).status_code
        == 403
    )
    body["new_key_proof"] = base64.b64encode(
        new_key.sign(b"TEAPASS_KEY_POSSESSION_V1\0" + command_bytes(c))
    ).decode()
    result = env.client.post("/v1/actors/lifecycle", json=body, headers=env.headers("admin"))
    assert result.status_code == 200, result.text
    old_signed = env.batch(external_id="AFTER-ROTATION")
    assert (
        env.client.post(
            "/v1/batches", json=old_signed, headers=env.headers(key="old-signing-key")
        ).status_code
        == 403
    )
    env.identities["grower"].key = new_key
    new_signed = env.batch(external_id="AFTER-ROTATION")
    assert (
        env.client.post(
            "/v1/batches", json=new_signed, headers=env.headers(key="new-signing-key")
        ).status_code
        == 201
    )
    with env.app.state.sessions() as db:
        original = db.scalar(
            select(BatchEvent).where(BatchEvent.id == recorded[0]["command"]["operation_id"])
        )
        assert original.signing_public_key == old_public


def test_admin_cannot_change_another_tenant_or_manage_admins(env):
    for target in ["other", "admin"]:
        _, body = command(env, "SET_ACTIVE", target=target, active=False)
        assert (
            env.client.post(
                "/v1/actors/lifecycle", json=body, headers=env.headers("admin")
            ).status_code
            == 404
        )
    _, body = command(env, "SET_ACTIVE", name="grower", active=False)
    assert (
        env.client.post("/v1/actors/lifecycle", json=body, headers=env.headers()).status_code == 403
    )
