# Backend implementation and release gates

Updated 19 October 2026. The backend and real local Midnight protocol now run. This is a tested local implementation, not a production release or a complete browser product.

## Implemented and exercised

| Area | Evidence and boundary |
| --- | --- |
| M0 compatibility | Compact 0.31.1, runtime 0.16.0 and Midnight.js 4.1.1; real private proof settled on local node/indexer/prover |
| M1 issuance | Cryptographic governance/issuer witnesses, material permissions, issuer revocation, salted domain-bound notes, issuance replay prevention |
| M2 inventory | Owner-authorized transfer, 1→2 split, 2→3 partial blend, green-leaf processing with explicit synthetic 15–35% yield; atomic commitment/nullifier transitions |
| M3 operational ledger | OIDC, tenant/role checks, signed immutable events, idempotent offline retries, dual-signed custody, discrepancy/rejection responses, bounded tenant-filtered declared lineage |
| M4 laboratory | Approved lab writes authenticated commitment; private reading threshold proof; batch/policy binding; expiry and live revocation checks |
| Current proof verification | Public proof endpoint reads real finalized state through a read-only verifier, compares every verifier key to the compiled build, and fails closed on unavailability/staleness |
| Durable chain intent | Signed preparation/submission jobs; receipt worker independently checks indexer + node canonical finality; clients cannot mark jobs finalized |
| Evidence access | Encrypted payloads, recipient-scoped expiring grants, revocation, immutable successful-access logs |
| Administration | Audited enrollment, signed actor deactivation, new-key possession requirement for rotation; historical event keys retained |
| Interoperability | Strict signed ObjectEvent EPCIS 2.0 profile with atomic import, idempotent replay and authorized export |
| Participant helpers | Browser WebCrypto signing/encryption, Python/JS canonical compatibility, IndexedDB queue adapter and conflict-preserving retry logic |
| Reproducibility | Docker services, migrations, lockfiles, compiler checksums, synthetic fixtures, local replay script, tests and public-only receipts |

## Current semantics

- `/v1/public/batches/{alias}` checks the contract-published batch reference, material class and exact policy before including a lab claim. It returns `VERIFIED_CLAIMS`, `INVALID_CLAIMS`, `UNAVAILABLE`, or `NOT_VERIFIED`; these apply only to the listed laboratory predicates, not blanket physical origin/safety.
- `/v1/public/proofs/{claim_id}` independently verifies the committed laboratory claim and its current status. It identifies the exact note commitment, lab authority, analyte/method/unit, threshold and policy. A revoked or expired claim is `INVALID`.
- A chain job marked `FINALIZED` means its receipt touched the pinned contract and is on the node's finalized canonical chain. It does **not** prove that every client-declared batch/edge/output matches that call's private inputs. `semantic_verification` remains `NOT_VERIFIED` on those jobs/edges.
- Custody acknowledgement is a physical-process record. It does not mutate inventory ownership or authorize a Compact spend.
- Negative devnet cases reject during generated-circuit execution against indexed state, before transaction submission. Positive transactions have real receipts. Do not relabel negative cases as rejected network transactions.

## Remaining release work

1. Connect the existing frontend to OIDC/PKCE, participant key storage, local wallet/prover, signing queue and API. The SDK exists; browser login, mobile offline persistence and recovery have not been end-to-end validated. Existing frontend changes were preserved.
2. Bind prepared job IDs and all declared lineage edges to exact private call inputs/outputs before promoting declared transformation history to cryptographically verified lineage. Public laboratory claims now check exact batch/material/policy binding. Add durable participant transaction recovery around crash-after-submit and ambiguous timeouts; the backend tracks submitted IDs but never holds wallet secrets.
3. Add broader EPCIS TransformationEvent/quantity mappings and external CSV adapters on the participant side. Current import supports only the documented signed ObjectEvent profile; it rejects unsupported plaintext commercial fields. No Tea Board/GTAC integration is claimed.
4. Add institution-verified issuer/lab enrollment, credential recovery and governance-key rotation/multisig; admin recovery remains an offline procedure. The demo's regulatory-looking values are explicitly synthetic.
5. Connect the implemented recipient key wrapping to authenticated key enrollment/recovery, evidence-file storage/scanning/retention, facility operations and organizational onboarding screens. Current evidence is a bounded opaque encrypted payload; no malware-scanned document upload service is claimed.
6. Before public deployment: configure non-owner DB credentials, evaluate tenant RLS, set HTTPS/edge quotas and operational alerts, exercise backups/restores and migration rollouts, scan dependencies/images, load-test, and obtain independent cryptographic/security review. No public SLA, production approval, or guaranteed free hosting is established.

CI is supplied but has not run remotely. Tests and live evidence are detailed in `PROOF.md`. User input is not needed for further local engineering; real onboarding needs a named approving institution/operator, authorized records/policies, and deployment ownership.
