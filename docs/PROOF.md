# Execution evidence — 19 October 2026

## Actual local Midnight network

- Amount probe: **4/4 live checks passed**, 46.81 seconds. `artifacts/midnight/amount-probe-local.json` contains deployment and private commitment receipts.
- Inventory/laboratory: **6/6 live checks passed**, 259.58 seconds. `artifacts/midnight/inventory-local.json` contains ten settled transactions: deployment, issuer approval, two issuances, blend, lab approval, policy registration, lab anchor, compliance proof and lab revocation.
- Inventory address: `774a4f1b8ba8eedfd071618ac823d80d7661cd862ff781a50bb666def9f8d83a` on local `undeployed` network.
- Exact compiled source SHA-256: `73407e06f1782da759a5642b459a8ecdf50da9f51204114ea159b422d1ed85db`.
- Backend receipt reconciliation independently returned `FINALIZED` for all ten transactions using indexer records and node canonical finality.
- Public proof verifier matched all deployed circuit verifier keys to the compiled build. The actual claim is `INVALID` with `LAB_REVOKED`, retained in `artifacts/midnight/public-claims-local.json`. It may additionally become expired over time.
- **Four real API-to-chain alias tests passed**: matching reference reflects revocation; wrong batch reference, material class and policy are rejected as unverified. These are opt-in tests; the ordinary backend run skips them explicitly.
- FastAPI → verifier → node/indexer end-to-end request returned HTTP 200 for that invalid claim. Public output excluded measurement, quantity, recipe and secrets.

The positive cases are real proof-server calls and settled local transactions. Negative cases (forged issuance, inflation, double spend, wrong-batch evidence) fail during compiled-circuit execution against indexed chain state, before submission. This is not evidence of a submitted invalid transaction being rejected by the node.

The local genesis wallet is public synthetic test infrastructure. No user wallet, real funds or public-network deployment was used. No explorer links exist for this ephemeral local network. Resetting its volumes invalidates the saved addresses as live references.

## Automated tests

- **67 PostgreSQL tests passed**, after migrations 0001–0003. Signed commands, tenant/role isolation, concurrent idempotency and history, custody races, expiry/revocation, lab grants, audited actor rotation/deactivation, EPCIS profile round trips, chain receipt state transitions and public proof allowlists are covered. External dependency failures in unit cases use explicitly mocked HTTP; the receipt and public-proof checks above used the real devnet.
- **33 generated Compact runtime tests passed** (24 inventory/lab/current-status tests + 9 amount-probe tests), also after clean `npm ci`.
- **8 participant SDK tests passed**, including JS→Python signature verification, Unicode canonicalization, AES-GCM context binding, nonextractable signing keys recipient-encrypted key wrapping, and offline retry/conflict behavior.
- TypeScript typecheck and Python Ruff checks passed.
- One test dependency warning remains: Starlette's httpx test adapter is deprecated; test assertions pass. Generated Compact sourcemaps reference missing original source locations; compilation/runtime behavior is unaffected.

Browser IndexedDB persistence, complete OIDC login, mobile UX, production throughput and institutional data quality are not established by these tests. Local lifecycle timings combine proof generation and settlement; they are not p95 throughput benchmarks.

## Reproduction

```sh
scripts/replay-judges.sh
```

This installs the checksum-pinned compiler, starts the local devnet, installs locked packages, generates real keys, runs runtime and live tests, and exports current public-claim evidence. The final live scenario intentionally revokes its lab, so a successful verification demonstrates `INVALID`, not a perpetual green badge. See `JUDGES.md` for API and test commands.

CI configurations exist but have not run on GitHub in this session. No production certification or independent cryptographic audit is claimed.


## Running service verification

The API image was rebuilt with frozen production dependencies, migrations 0001–0003 applied, and read-only/non-root container startup verified. The actual containerized public endpoint returned the revoked claim through the local verifier. Database model/migration drift was checked with `alembic check`. The initial indexer image architecture, WASM duplication and historical-query issues were resolved before recording successful evidence; failed attempts are not counted as passes.
