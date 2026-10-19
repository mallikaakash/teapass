# TeaPass

Confidential tea traceability, designed around Midnight Compact contracts and an operational event ledger.

**Current state: a tested backend plus real local Midnight Compact proofs. Not yet production-ready or a complete browser product.** The [specification](TeaPass_Complete_Product_Technical_Spec_v1.md) is the baseline; existing frontend work is preserved.

Wave 2 pitch materials for judges: [slide deck](docs/submission/akindo-wave2-deck.pdf) and [video pitch](docs/submission/akindo-wave2-pitch.mp4). The Midnight code in this repository is Apache-2.0. Compile and replay it with `scripts/replay-judges.sh`. The saved receipts are local `undeployed` devnet evidence, not a public-network deployment.

## Implemented

- OIDC-authenticated FastAPI/PostgreSQL ledger with tenant/role checks, signed immutable events, idempotent retries and concurrent-update protection.
- Dual-signed custody, discrepancy handling, scoped expiring auditor grants, encrypted lab records, audited actor deactivation and signing-key rotation.
- Real Compact contracts for authorized issuance, transfers, splits, conserved private blending, processing and authenticated lab threshold proofs.
- Durable chain intents and receipt reconciliation against the configured indexer and node's finalized canonical chain.
- Current public proof verification with exact compiled verifier-key checks, lab/policy revocation and expiry. Public aliases include only claims with matching note batch reference, material class and policy.
- WebCrypto client helpers, recipient-encrypted data-key envelopes, durable queue adapter, strict signed EPCIS ObjectEvent import/export, and deterministic fictional fixtures.
- 67 PostgreSQL tests, 33 compiled-runtime tests, 10 live devnet checks and 8 client SDK tests. Live receipts are under `artifacts/midnight/`.

For the actual proof lifecycle run `scripts/replay-judges.sh`; see [the replay guide](docs/JUDGES.md) and [execution evidence](docs/PROOF.md). This uses local synthetic services and no paid account.

## Run locally without a paid service

Prerequisites: Docker Compose. The configuration below is **local development only**, with loopback ports and publicly known development credentials.

```sh
docker compose --profile identity up --build -d
curl http://localhost:8000/health/ready
```

API schema: http://localhost:8000/docs. Keycloak: http://localhost:8080, local bootstrap admin `local-admin`, password `local-only-change-before-sharing`. Realm `teapass` imports with registration disabled and a public `teapass-web` client requiring authorization code + PKCE. No user accounts are seeded. The frontend callback is not implemented yet. See [Keycloak's container guide](https://www.keycloak.org/server/containers) for the development mode and import behavior.

The API accepts access tokens with issuer `http://localhost:8080/realms/teapass` and audience `teapass-api`. Bearer identity alone is insufficient: a corresponding active actor and organization must exist in PostgreSQL. Identity-provider failure denies access.

To bootstrap an organization, first create an identity in the local identity provider and obtain its subject ID. Provide only the participant's **public** Ed25519 key, base64 encoded, in a file accessible to the bootstrap command. From `apps/api/`, with the database running:

```sh
uv sync --frozen
uv run python -m teapass.bootstrap \
  --organization 'Synthetic Tea Cooperative' \
  --subject '<OIDC subject ID>' \
  --signing-public-key-file /absolute/path/to/public-key.txt
```

This creates that organization's first admin. The admin may enroll grower/factory/blender/lab/buyer/auditor identities through `POST /v1/actors`; an admin cannot mint notes or manufacture a lab proof. Public-key enrollment must use a separately trusted channel. Signing keys remain on participants' devices.

For host development, copy `.env.example` to `apps/api/.env` and run from `apps/api/`:

```sh
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn teapass.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Do not run the host API and Compose API on the same port simultaneously. `/health/ready` checks the database migration; its chain field indicates configuration, not a live consensus check. The public proof endpoint performs current chain verification.

## Signing and client integration

Use `GET /v1/me` for the enrolled actor ID, organization ID, and deployment ID. Full request schemas are in OpenAPI. Every command has a client-generated UUID operation ID and every mutating API request requires `Idempotency-Key`.

See [the signing contract](docs/API_SIGNING.md). The application hash chain is independent of Compact note commitments. Do not reuse its SHA-256 encoding as a guessed Midnight circuit hash.

## Tests

The suite uses real PostgreSQL, including migrations, concurrent retry races, and append-only triggers. It deliberately drops and recreates the `public` schema in the test database before each case. The database name must end in `_test`. Never point it at a database containing useful data.

```sh
docker run --rm -d --name teapass-api-test-db \
  -e POSTGRES_USER=teapass -e POSTGRES_PASSWORD=local-only \
  -e POSTGRES_DB=teapass_test -p 127.0.0.1:55433:5432 postgres:17.6-alpine
cd apps/api
uv sync --frozen
TEAPASS_TEST_DATABASE_URL=postgresql+psycopg://teapass:local-only@127.0.0.1:55433/teapass_test uv run pytest -q
uv run ruff check .
uv run ruff format --check .
docker stop teapass-api-test-db
```

Wait for PostgreSQL readiness before running tests. Test authentication uses freshly generated RSA keys restricted to `environment=test`; deployment authentication has no bypass.

## Remaining release work

[Backend status](docs/BACKEND_STATUS.md) records precise implemented boundaries and remaining gates. The existing frontend still needs the full OIDC/wallet/prover/offline flow wired to this backend. Declared job/lineage metadata still needs exact binding to private call inputs and outputs before it can be labeled verified. Public lab claims already check batch/material/policy bindings. Broader interoperability, facility/document workflows, participant recovery and institution enrollment remain release work.

Before production: independently review the protocol; establish approvers/policies and recovery; provision non-owner DB credentials and HTTPS; apply shared quotas, monitoring and alerting; run backup/restore and load tests; review image/dependency pins. See [threat model](docs/THREAT_MODEL.md) and [privacy boundaries](docs/PRIVACY_BOUNDARIES.md). Free local operation does not guarantee free reliable public hosting.
