import base64
import os
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from teapass.config import Settings
from teapass.main import create_app
from teapass.models import Actor, Organization
from teapass.schemas import AppendEventCommand, CreateBatchCommand
from teapass.security import command_bytes


@pytest.fixture(scope="session")
def database_url():
    url = os.environ.get("TEAPASS_TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEAPASS_TEST_DATABASE_URL must point to a dedicated PostgreSQL test database")
    # Fail closed: the suite drops the schema between cases.
    from sqlalchemy.engine import make_url

    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Test database name must end in _test")
    return url


@pytest.fixture
def env(database_url, monkeypatch):
    monkeypatch.setenv("TEAPASS_DATABASE_URL", database_url)
    engine = create_engine(database_url)
    with engine.begin() as db:
        db.execute(text("DROP SCHEMA public CASCADE"))
        db.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
    engine.dispose()
    jwt_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = jwt_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    settings = Settings(
        environment="test", database_url=database_url, jwt_public_key=public_key.decode()
    )
    app = create_app(settings)
    identities = {}
    with app.state.sessions() as db, db.begin():
        organizations = [Organization(name="Synthetic A"), Organization(name="Synthetic B")]
        db.add_all(organizations)
        db.flush()
        for name, role, org in [
            ("grower", "grower", 0),
            ("other", "grower", 1),
            ("buyer", "buyer", 0),
            ("admin", "admin", 0),
            ("lab", "lab", 0),
            ("auditor", "auditor", 0),
        ]:
            signing_key = ed25519.Ed25519PrivateKey.generate()
            actor = Actor(
                org_id=organizations[org].id,
                subject=name,
                role=role,
                signing_public_key=signing_key.public_key().public_bytes_raw(),
            )
            db.add(actor)
            db.flush()
            identities[name] = SimpleNamespace(actor=actor, key=signing_key)

    def token(name="grower", **overrides):
        now = int(time.time())
        claims = dict(
            sub=name, iss=settings.oidc_issuer, aud=settings.oidc_audience, iat=now, exp=now + 300
        )
        claims.update(overrides)
        return jwt.encode(claims, jwt_key, algorithm="RS256")

    def headers(name="grower", key="operation-0001", **overrides):
        return {"Authorization": "Bearer " + token(name, **overrides), "Idempotency-Key": key}

    def signed(payload, name="grower"):
        cls = (
            CreateBatchCommand if payload["command_type"] == "CREATE_BATCH" else AppendEventCommand
        )
        parsed = cls.model_validate(payload)
        signature = identities[name].key.sign(command_bytes(parsed))
        return {
            "command": parsed.model_dump(mode="json"),
            "signature": base64.b64encode(signature).decode(),
        }

    def batch(name="grower", **overrides):
        actor = identities[name].actor
        payload = dict(
            schema_version="1.0",
            deployment_id=settings.deployment_id,
            actor_id=str(actor.id),
            org_id=str(actor.org_id),
            operation_id=str(uuid4()),
            batch_id=str(uuid4()),
            occurred_at="2026-01-01T00:00:00Z",
            command_type="CREATE_BATCH",
            external_id="PRIVATE-SUPPLIER-001",
            public_alias="BATCH-" + uuid4().hex,
            material_class="GREEN_LEAF",
            published=True,
            synthetic=True,
        )
        payload.update(overrides)
        return signed(payload, name)

    with TestClient(app) as client:
        yield SimpleNamespace(
            app=app,
            client=client,
            identities=identities,
            settings=settings,
            token=token,
            headers=headers,
            signed=signed,
            batch=batch,
        )


@pytest.fixture
def recorded(env):
    body = env.batch()
    response = env.client.post("/v1/batches", json=body, headers=env.headers())
    assert response.status_code == 201, response.text
    return body, response.json()
