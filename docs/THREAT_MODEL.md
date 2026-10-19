# Threat model and release limits

| Threat | Current control | Residual risk |
| --- | --- | --- |
| Forged issuance/lab record | Compact authority witnesses and approved registries | Governance and institution identity still need independent review |
| Inflation/double spending | Bounded arithmetic, exact conservation, commitment membership, atomic owner-bound nullifiers | Independent cryptographic review and broader property/fuzz testing still required |
| Replayed signed command | Deployment domain, unique operation IDs, actor-scoped transactional idempotency | Participant must preserve original signed command across uncertain network responses |
| Concurrent history fork | Batch row lock and exact previous event hash | Hot-batch contention; production load targets unmeasured |
| Revoked credentials | Active actor/org database checks, serialized actor requests; live lab/policy checks | Org/admin recovery and governance-key rotation remain operational procedures |
| Tenant leakage | Scoped queries, recipient grants, public schema allowlists | DB RLS not yet installed; direct database access is privileged |
| Event/audit editing | No UPDATE/DELETE/TRUNCATE triggers, historic key snapshots | Database owner can disable controls; external event anchoring pending |
| False finality | Indexer receipt plus node finalized height and canonical hash | Configured node/indexer trust; no consensus light-client proof |
| Contract replacement | Compare every deployed verifier key to compiled build | Build provenance/deployment governance require operator review |
| Public proof fabrication | No client-set verification flag; current chain read and strict response binding | Alias/job metadata still not fully bound to exact private note inputs |
| Private evidence theft | Participant AES-GCM, recipient key wrapping, expiry/revocation | Compromised participant device and already-downloaded evidence cannot be recalled |
| Request abuse | Body bounds, bounded pages/traversals, SQL timeouts, verifier concurrency cap | Add shared edge quotas, alerts and load tests before public exposure |
| Physical fraud/copied QR | Explicit public limitations and separate custody evidence | No cryptographic guarantee about physical tea without reliable attestors/sampling |

`infra/postgres/runtime-role.sql` provides capability restrictions for a separately provisioned runtime login. Apply after migrations with the schema owner, then use that runtime login in the API. Local Compose deliberately uses development credentials and is not a production configuration. Review role grants after each schema change.

Production go-live requires institution authorization, policy validation, participant key recovery, secure hosting, successful restore drills, migration rollout, dependency/image review, monitoring, realistic load/privacy tests and independent protocol review. No test suite here is a certification of those external requirements.
