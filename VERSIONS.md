# Version evidence — 19 October 2026

## Operational backend

Exact direct and transitive Python dependencies, platform wheels and hashes are committed in `apps/api/uv.lock`. Use `uv sync --frozen`; do not regenerate pins during deployment.

| Component | Tested version |
| --- | --- |
| Host Python | 3.13.11 |
| Container Python | 3.13.16 |
| Host uv / container uv | 0.11.7 / 0.9.4 |
| FastAPI / Starlette | 0.146.0 / 1.9.0 |
| Pydantic / pydantic-settings | 2.14.1 / 2.16.0 |
| SQLAlchemy / psycopg | 2.0.55 / 3.3.6 |
| Alembic | 1.20.0 |
| PyJWT / cryptography | 2.15.1 / 50.0.2 |
| RFC 8785 implementation | 0.1.4 |
| pytest / Ruff | 9.1.1 / 0.17.1 |
| PostgreSQL test image | 17.6-alpine |
| Docker daemon | 29.1.3 |

The PostgreSQL and Python container image digests are pinned in Compose/Dockerfile. These are reproducibility pins for the local foundation, not a security sign-off; patch review and vulnerability scanning are required before a public deployment.

Optional local Keycloak image: `quay.io/keycloak/keycloak:26.8.1`, selected from the official [download page](https://www.keycloak.org/downloads). The realm configuration is provided; browser login and the complete OIDC flow are not yet validated. Its image is not yet pinned to a digest.

## Midnight protocol — compiled and proven locally

| Component | Working pin |
| --- | --- |
| Compact CLI / compiler | 0.5.1 / 0.31.1 |
| Compiler ledger target | ledger-8.0.2 |
| Compact runtime | 0.16.0 |
| On-chain WASM runtime v3 | 3.0.0, single physical installation |
| Compact.js via protocol | 2.5.1 |
| Midnight.js / testkit | 4.1.1 |
| Wallet SDK | 1.2.0 |
| Node | 1.0.400 |
| Indexer | 4.3.5 (native ARM64 image on this host) |
| Proof server | 8.1.3 |
| Host Node.js | 25.3.0; CI targets Node 22 (remote CI not run) |

Compiler download SHA-256 values are pinned per architecture in `scripts/install-compact.sh`. Images are pinned by digest in `infra/midnight/compose.yml` and `scripts/midnight-devnet.sh`. `packages/compact-contracts/package-lock.json` locks the full JavaScript graph. Generated key material/build output is ignored and reproduced from source, not committed.

The official [support matrix](https://docs.midnight.network/relnotes/support-matrix) was checked, and both the minimal proof and inventory/lab lifecycle settled using these pins. Newer compiler/runtime releases target a different ledger generation; do not update components independently.

Compatibility findings: the indexer default tag was AMD64-only, so the startup script selects the native ARM64 digest when needed. The indexer requires the node beyond genesis, handled by the node health check. Two physical WASM runtime copies caused `StateValue` type failures despite identical package versions; overrides plus a deduplicated lockfile fixed this, and a clean `npm ci` was verified. npm reported zero known vulnerabilities at installation; this is not a security audit.
