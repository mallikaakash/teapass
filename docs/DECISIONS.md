# Engineering decisions — 19 October 2026

The user requested production-oriented backend implementation, Midnight Compact/Web3, and free infrastructure. No cloud provider, governance approver or institutional data was specified. Local Docker services and participant-controlled proving are the defaults; no paid resources or public-network wallet transactions were created.

| Decision | Implementation and boundary |
| --- | --- |
| API/data | FastAPI + PostgreSQL, separate from the frontend; tenant checks in application queries, immutable event/audit triggers |
| Identity | External OIDC RS256 tokens; optional local Keycloak with PKCE; database roles/active status are authoritative |
| Governance | One cryptographic governance key approves issuer material classes, labs and immutable policy versions; application admin permissions do not grant chain authority |
| Commitment | Compact `persistentCommit` over a typed note, contract address, network domain and protocol domain, with a random salt; operational SHA-256 is a separate format |
| Spend identity | Nullifier hashes contract/network, the complete note commitment, and owner secret. Independent notes sharing a nonce remain independently spendable |
| Arity | Transfer 1→1, split 1→2, blend 2→3 with two positive remainders; full-consumption/general multi-input blending is not supported yet |
| Processing | Input = made tea + waste + loss, 15–35% synthetic yield bounds; no regulatory/physical truth guarantee |
| Lab authenticity | Approved lab proves authority while anchoring a batch-bound salted record. Compliance references that anchor; client flags cannot establish lab authority |
| Time | Policy window + sample age + record expiry checked in Compact. Public claims expire at the earlier of record expiry and max sample age; current lab/policy revocation is checked again |
| Metadata privacy | Amounts, salts, measurements, recipes and authority secrets are private witnesses. Public note commitment membership lookups reveal links; graph anonymity is not claimed |
| Proof verification | Every deployed verifier key must match the local compiled inventory build. Latest indexed action is checked against node canonical finality, with indexer catch-up required |
| API transaction meaning | Prepared/submitted/finalized receipt status is separate from semantic binding of client-declared batches to private notes. Laboratory claims are checked against published note batch references, material and policy before appearing on an alias |
| Custody | Sender's signed offer + receiver's signed response bound to exact offer hash and event head; conflicts require re-signing; no automatic ownership transfer |
| Grants | Explicit recipient + batch + scope + expiry; successful disclosure accesses logged; participant supplies encrypted key envelope |
| Actor lifecycle | Org admin may deactivate/rotate non-admin actors; new key must prove possession; old event key snapshots retained. Admin recovery is offline |
| Interoperability | Bounded, strict signed EPCIS ObjectEvent profile; no arbitrary remote JSON-LD context resolution or plaintext quantity ingestion |
| Free operation | Local node, indexer, prover, Postgres and optional identity provider. Real public operation and proving capacity may have costs |

The supported version matrix is pinned in `VERSIONS.md`. Compilation and local receipts, rather than documentation alone, establish compatibility. Midnight's WASM runtime must be deduplicated physically as well as version-pinned; the lockfile was checked with a fresh `npm ci`.

Before a real pilot the user must designate authorized organization/issuer/lab approvers, supply permitted policies/sample records, agree on data sharing/recovery, and choose deployment ownership. Never send seeds or private keys through chat.
