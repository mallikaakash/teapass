# Local replay and verification

Everything below uses local synthetic infrastructure. Docker and Node 22+ are required; the host run used Node 25.3.0. The compiler installer supports macOS/Linux ARM64 and x86_64 with pinned hashes.

## Real proof lifecycle

From repository root:

```sh
scripts/replay-judges.sh
```

Expect two proof suites: amount probe (4 checks) and inventory/lab lifecycle (6 checks). The inventory scenario issues 100 kg and 80 kg **made tea** notes, proves two 40 kg remainders and a 100 kg blend, proves an authenticated synthetic lab threshold, and then revokes the lab. Failures are not converted to success badges.

Review `artifacts/midnight/inventory-local.json` for receipts and exact source hash. `public-claims-local.json` records current invalidity after revocation. Synthetic policy identifiers are hashes, not claims of compliance with a real regulatory standard.

To run the current-state verifier after the replay:

```sh
scripts/start-local-verifier.sh
```

In a separate terminal, start the API with the public contract address from the receipt, `TEAPASS_MIDNIGHT_NETWORK=undeployed`, and `TEAPASS_MIDNIGHT_VERIFIER_URL=http://127.0.0.1:6301`. A containerized API on Docker Desktop can use `infra/midnight/api.override.yml` and `http://host.docker.internal:6301`; Linux host/container routing must be configured for that environment. No loopback verifier should be opened to the public directly.

```sh
# Set TEAPASS_MIDNIGHT_CONTRACT_ADDRESS to the address in the successful local receipt first.
docker compose -f docker-compose.yml -f infra/midnight/api.override.yml up --build -d api
```

`GET /v1/public/proofs/{claimId}` returns current status, exact note commitment, policy and lab authority, canonical finalized block reference and check time. `GET /v1/public/batches/{alias}` evaluates attached lab claims only after checking the exact deployment-bound batch reference, material class and policy. Unbound claims do not receive a verified badge.

## Backend and participant helpers

```sh
# Start the disposable database only if it is not already running.
docker run --rm -d --name teapass-api-test-db \
  -e POSTGRES_USER=teapass -e POSTGRES_PASSWORD=local-only \
  -e POSTGRES_DB=teapass_test -p 127.0.0.1:55433:5432 postgres:17.6-alpine
cd apps/api
uv sync --frozen
TEAPASS_TEST_DATABASE_URL=postgresql+psycopg://teapass:local-only@127.0.0.1:55433/teapass_test uv run pytest -q
uv run ruff check .
uv run ruff format --check .
cd ../../packages/client-sdk
npm test
```

The backend suite resets the dedicated `_test` database schema. Do not use a database with useful data. `python scripts/generate-fixtures.py` recreates deterministic fictional fixtures; it does not create chain proofs or enroll people.

## Receipt reconciliation

Configure the API database, network, pinned contract, indexer and node URLs, then run from `apps/api`:

```sh
uv run python -m teapass.reconcile --once
# Omit --once for a foreground worker with 30-second polling.
```

The worker checks submitted IDs, validates contract inclusion, checks node finality/canonical block hashes, and rechecks prior receipts. Dependency failures produce `RECHECK_REQUIRED`; partial failures never become finalized successful inventory operations. It does not submit transactions, possess private keys, or certify that client-declared lineage matches private witnesses.


The four real alias-binding API checks are opt-in:

```sh
TEAPASS_LIVE_CHAIN_EVIDENCE=/absolute/path/to/teapass/artifacts/midnight/inventory-local.json \
TEAPASS_TEST_DATABASE_URL=postgresql+psycopg://teapass:local-only@127.0.0.1:55433/teapass_test \
apps/api/.venv/bin/pytest -q apps/api/tests/test_live_public_binding.py
```

Start the verifier first and run `src/verify-local-evidence.ts` after each new devnet replay to refresh the claim artifact. These tests reset only the dedicated test DB, not the devnet or local application DB.
