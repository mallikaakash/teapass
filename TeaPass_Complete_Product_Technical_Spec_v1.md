# TeaPass — Complete Product, Protocol & Implementation Specification

**Version:** 1.0 (design baseline)  
**Date:** 19 October 2026  
**Challenge:** NESFIC 2026, Industry I-08, End-to-End Digital Traceability of Tea Across the Assam Tea Value Chain  
**Buildathon target:** Midnight AKINDO (subject to applicable wave rules)  
**Status:** Proposed architecture; **not** an implemented, audited or deployed system.  
**Core engine:** Private Proof of Transformation (PPT), an application-level confidential inventory and provenance verification protocol.

> **One-sentence product definition:** TeaPass allows Assam tea supply-chain participants to record batch custody, processing, blending and laboratory evidence, while allowing buyers and auditors to verify selected integrity and compliance claims without automatically disclosing the participants' confidential procurement data or blend recipes.

> **Non-negotiable honesty boundary:** A proof attests that authenticated digital records meet encoded rules; it does **not** prove that real leaves originated where a person claims, that sample collection was honest, that a printed QR was not copied, or that all safety requirements are satisfied.

---

## 0. Executive decision and delivery strategy

Build **two layers** but **one product**:

1. **PPT engine / Midnight subsystem:** a reusable, cryptographically enforceable inventory-note registry that supports authorized issuance, atomic consumption, partial splits, blending and bound compliance attestations.
2. **TeaPass application:** an interoperable tea supply-chain workflow, provenance graph, batch importer, mobile-friendly role-based interface, QR verification and audit export.

Do **not** build a token marketplace, NFT marketplace, financial protocol, AI agent, carbon credit system or custom hardware. TeaPass is an operational traceability platform with a privacy-preserving verification subsystem.

**First runnable slice:** an authorized issuer mints two private inventory notes; the factory consumes them and creates a blend note plus remainders; a buyer independently verifies the rule without seeing the private recipe; an attempted double consumption fails on an actual Midnight local devnet. Add signed laboratory compliance next.

**Two external narratives, same codebase:**
- **AKINDO:** Focus on real compiled Compact circuits, state transitions, privacy guarantees, adversarial testing and deployment receipts.
- **NESFIC:** Focus on end-to-end tea workflow, low-connectivity data capture, data quality, integration with Tea Board/GTAC, risk-aware compliance and believable pilot handoff.

---

## 1. Problem understanding, users and existing workflow

### 1.1 The business problem

The Assam tea ecosystem contains gardens, small tea growers, buying agents, bought-leaf factories, manufacturers, laboratories, warehouses, auction actors, blenders, exporters and buyers. Supply-chain records are distributed across different systems and paper documents. Source lots can be combined or subdivided, making simple one-QR-per-origin tracking insufficient. Data sharing is hampered by confidentiality concerns around suppliers, procurement, volume, prices and proprietary recipes.

The government challenge explicitly requests: green-leaf-to-market traceability; unique lot IDs; manufacturing, storage, auctions, blending and export events; MRL SOP and test-data capture; verifiable origin; interoperability with Tea Board India and Guwahati Tea Auction Centre (GTAC); cost-effective adoption; role-based access; and offline/low-connectivity consideration. Blockchain is an optional technique, not a requirement.

### 1.2 Personas

| Actor | Task | What they may view |
|---|---|---|
| Small grower | Register leaf lot, attest harvest/transfer, work offline | Own lots, receipts and transfer acknowledgments |
| Collection agent / factory intake | Record receipt, scale weight, reconcile with dispatch | Counterparty and received material |
| Processor / bought-leaf factory | Record processing yields and create manufactured batches | Own supply contracts, inputs, yields, outputs |
| Laboratory | Attach sample identity, result, method and signature | Test inputs and associated testing records |
| Blender / exporter | Consume inputs, produce blends, attach shipment evidence | Confidential formula and stock |
| Warehouse / auction participant | Record transfers and identifiers | Authorized consignment metadata |
| Buyer / importer | Verify origin/compliance/custody claims by QR | Claims and issuer status; not confidential source recipe |
| Regulator / delegated auditor | Review signed evidence and reconcile records | Explicitly authorized disclosure set; full disclosure is not implied |
| Platform operator | Operate infrastructure | Metadata needed for availability, never unencrypted business secrets by default |

### 1.3 Core value proposition

A consortium can verify **inventory constraints and selected compliance predicates across organizations** without forcing each party to disclose the full supplier graph to a common database operator. An ordinary signed PostgreSQL traceability application remains the baseline comparator. Use PPT only when the cross-organization confidentiality and shared-state requirement makes it valuable.

---

## 2. Product scope and release gates

### 2.1 P0 — AKINDO-quality cryptographic proof of concept (mandatory)

- [ ] Compact source compiles using pinned, mutually compatible toolchain/runtime/SDK versions.
- [ ] Contract tracks approved issuer authority or cryptographically bound issuer authorization.
- [ ] Unique commitments for inventory notes; precise fixed-point mass quantities.
- [ ] Atomic spend of existing notes using uniqueness-checked nullifiers.
- [ ] `issue`, `split`, and `transform` semantics. `split` may be implemented as a constrained transform.
- [ ] A public verifier can check contract validity without seeing inputs or exact blending ratio.
- [ ] Factory demo creates output and change notes, preserving mass balance.
- [ ] Duplicate consumption, inflation, forged source, wrong proof binding and replay tests fail.
- [ ] Testnet or local-devnet transaction receipts, exact build commands and replay walkthrough.

### 2.2 P1 — NESFIC-ready demo MVP (mandatory for a convincing application)

- [ ] Grower/factory/lab/blender/buyer roles, authentication and role-based permissions.
- [ ] End-to-end lot/event ledger in PostgreSQL with append-only signed events.
- [ ] Provenance graph with transformations, custody transitions and exception status.
- [ ] A simple laboratory certificate workflow with a real binding to a batch commitment.
- [ ] Private threshold-compliance proof or another concrete, correctly scoped predicate.
- [ ] QR landing page showing claims, valid/invalid status, issuer, evidence class, and limitations.
- [ ] Offline-capable grower record capture and idempotent sync; on-chain finalization after reconnect.
- [ ] Deterministic synthetic dataset and documented scenarios.
- [ ] Import/export adapter implementing selected GS1 EPCIS 2.0 semantics; CSV bridge for institutional integrations.
- [ ] 3–4 minute reproducible judging demo and screenshots.

### 2.3 P2 — Pilot and commercial work (not required for prototype)

- [ ] Real partner enrollment, signed scale/lab data, Tea Board / GTAC technical agreement.
- [ ] Policy engine per pesticide/analyte, jurisdiction, product, effective date and testing method.
- [ ] Delegated auditor access using encrypted evidence, auditable consent and revocation.
- [ ] Robust stock reconciliation against calibrated weighing systems and inventories.
- [ ] Multi-organization disaster recovery, credential rotation, off-chain recovery, telemetry and resilience.
- [ ] Cost/latency measurements on real activity volumes; alternatives comparison.
- [ ] Privacy attack analysis for metadata correlation and traffic patterns.

### 2.4 Explicit non-goals

No claim of governmental endorsement, quantum-safe implementation, regulatory certification, physical tamper prevention, real-world provenance verification without credible physical controls, completely hidden business graph, or fully private on-chain metadata. No real user personal data in public demos.

---

## 3. Solution workflows and UX specification

### 3.1 Grower registers an origin lot

1. On mobile, grower chooses `Create lot`, enters approximate quantity, leaf type, harvest date, source location (coarsened for consumer view) and offline evidence.
2. App creates locally unique operation ID and signed event; UI marks `Pending sync` until uploaded.
3. Upon connectivity, a registered issuer/receiving institution attests validated lot metadata and authorizes PPT issuance.
4. A new private inventory note commitment becomes the cryptographic supply-chain root. Status advances through `Recorded -> Attested -> Committed`.
5. All public-origin language must reflect the actual attestation source: `Attested by [issuer]`, not `Government-verified` without government authorization.

### 3.2 Intake and processing

1. Factory scans or enters lot ID; weights are compared with dispatch record.
2. Both dispatch and receipt are acknowledged; disagreements create an exception, not silent overwrite.
3. For manufacturing, capture leaf mass, made-tea output mass, process loss/waste, and reason codes.
4. PPT verifies a configured transformation relation, not always exact equality of input and saleable output.
5. New made-tea note is bound to transformed product type and appropriate inherited provenance class.

### 3.3 Private blend

1. Blender chooses two or more available input notes and target quantities.
2. UI displays source identities and recipe **only** to the authorized blender.
3. Backend / controlled client prepares witness inputs, note ownership authority, nullifiers, output commitments and private remainder notes.
4. Contract verifies input commitments exist, have valid unspent state, are authorized, and consumed quantities plus remainder sum to input notes; outputs satisfy configured mass-balance constraints.
5. Atomic ledger transition marks input nullifiers spent and registers all output commitments. If transaction fails, no input is consumed.
6. Buyer receives a public claim proof for output `BLEND-001`, not raw formula.

### 3.4 Laboratory compliance

1. Registered lab binds a sample, source/output batch commitment, analyte ID, result, unit, sampling time, method and policy to a signed attestation.
2. Evidence is private/encrypted off-chain; cryptographic commitment is published only as required.
3. Private circuit proves a nonnegative fixed-point measurement satisfies the **specified** threshold, test validity window and batch linkage. It verifies authenticated issuer authority using a circuit-supported proof or anchored authorization flow.
4. UI shows: `Claim X passed against policy Y using lab credential Z`, NOT blanket `food safe`.
5. Revoked/expired credentials cause subsequent verification to display exception status. Historical proofs are preserved but labeled according to current validity rules.

### 3.5 Public buyer QR scan

`GET /v1/public/batches/BLEND-001` returns publicly authorized fields only: batch alias, claim definitions, issuing institution, policy version, time, on-chain transaction reference, proofs/contract status, product category, limitations and a freshness timestamp. A QR is a pointer to this verification record; a copied QR does not certify the physical packet. QR should optionally include serial/tamper-evident packing integration in later pilots.

### 3.6 Auditor view

Auditor requests a specific scope (e.g. `Batch BLEND-001, issuer and input certificate trail`) and gets time-limited access to encrypted evidentiary records after authorized-party consent. Auditor verifies documents against commitments and event signatures; access grants/requests are logged. `Open` does not automatically mean `publish on-chain`.

### 3.7 Screens and behavior

1. **System overview:** lot counts, exception queue, actor role, verification status, synthetic-demo ribbon.
2. **Register lot:** simple mobile flow, optional document photo, location, scale, offline status.
3. **Inventory:** note balance, owner, batch IDs, unspent/spent status, private versus public badges.
4. **Transform / Blend:** input selection, private quantities, output target, proof generation and finality indicators.
5. **Lab certification:** certificate form, issuer identity, threshold/policy, proof result.
6. **Provenance explorer:** role-filtered graph with public/private edges and verifiable transitions.
7. **QR buyer view:** origin claim, compliance claim, certification status, latest verification checkpoint, limitations.
8. **Auditor portal:** scoped evidence request, audit access log, evidence hash comparison.
9. **Judge replay:** seeded happy path and buttons for preconfigured adversarial transactions, with actual receipt/error output.

---

## 4. Architecture and trust boundaries

```text
Grower PWA -----\
Factory Console --\              +------------------------------+
Lab Portal --------> API Gateway ->| Traceability Service        |--> PostgreSQL
Blender Console ---/              | Actor Registry             |--> Encrypted Object Storage
Buyer QR ---------/               | EPCIS Adapter + Event Log  |--> Read-only Event Indexer
                                  +---------------+--------------+
                                                  |
                                      orchestrates transactions
                                                  v
Private inputs --> CLIENT/CONTROLLED PROVER --> Midnight.js + Compact contract
    |                  |                             |
    |          Never publish raw witnesses           +--> Public commitments
    |                                                +--> Spent nullifiers
    +--> Encrypted role-scoped storage               +--> Approved issuer state
                                                    +--> Policy version hashes

Institutional systems (Tea Board / GTAC) <--> Versioned CSV / EPCIS-compatible adapters
```

**Important:** Midnight witness data must never be sent to an untrusted hosted proof server. For local demonstration, run the proof server locally. For a multi-tenant pilot, consider participant-controlled proving or a carefully threat-modeled private deployment; documentation and actual toolchain behavior must be verified before release.

### 4.1 Components and stack

| Layer | Proposed stack | Purpose |
|---|---|---|
| Web | Next.js, TypeScript, Tailwind, shadcn/ui | Main operator, buyer and judge interfaces |
| Mobile/offline | Responsive PWA + IndexedDB, service worker | Offline records, retry queue, limited field device requirements |
| API | FastAPI (Python) + Pydantic | Auth, actor & batch workflows, issuance approvals, reconciliation |
| DB | PostgreSQL | Actor directory, event ledger, private authorized metadata, import jobs |
| Evidence | S3-compatible object storage, server-side and envelope encryption | Photos, certificates, attachments, audit records |
| Blockchain | Compact + Midnight.js, compatible pinned versions | ZK execution, contract state, receipts |
| Indexer | Small TypeScript worker or Python poller | Chain checkpoint and transaction status reconciliation |
| Queue (optional P1) | Redis-backed task worker | Retries for attachment processing and chain status; never a source of truth |
| Observability | OpenTelemetry/structured logs; simple Prometheus metrics | Trace failures without logging secrets |
| Deployment | Docker Compose local; managed Postgres + cloud runtime for web/API | Reproducible demo and modest operating cost |

### 4.2 Consistency rules

- Postgres event records are not the source of truth for spent-note status; the Midnight contract is.
- `PENDING_PROOF`, `SUBMITTED`, `FINALIZED`, `REJECTED`, `REORG_OR_UNKNOWN` are distinct states. Do not mark output committed before confirmed finality.
- Use an idempotency key for every API command; a unique DB constraint prevents retry duplication.
- Never automatically re-mint after a timeout. Query on-chain state and reconcile first.
- All off-chain events use immutable event IDs, actor signatures, versioned schema and parent references. Correct mistakes with superseding events.
- Off-chain archive should not expose meaningful unsalted document hashes for low-entropy sensitive fields; use keyed/nonce-bearing commitments as suitable.

---

## 5. Cryptographic protocol: Private Proof of Transformation

### 5.1 Goals and adversary

**Security goals:** (a) no silent creation of extra privately accounted tea inventory through transforms; (b) one committed note cannot be spent twice; (c) invalid issuers cannot mint accepted roots; (d) buyer can verify a declared policy claim bound to an output batch; (e) private amounts/suppliers are not disclosed merely to check those rules.

**Adversaries:** malicious blender, fake grower, dishonest data submitter, compromised API, colluding participants, observer of all public ledger events, unauthorized buyer, and malicious replay client. Out of scope for cryptographic guarantee: colluding physical issuers claiming nonexistent tea, fake lab sampling, unauthorized physical mixing, QR cloning, device compromise, bribery of accredited labs, and all traffic analysis.

### 5.2 Note model

Logical private note (representation adapted to actual Compact supported types):

```text
InventoryNote {
  protocol_version
  note_id_random       // unpredictable unique nonce; never reuse
  owner_secret_or_pubkey_commitment
  issuer_id_or_issuer_commitment
  batch_private_ref
  material_class       // GREEN_LEAF / MADE_TEA / BLENDED_TEA ...
  quantity_mg_or_g     // nonnegative bounded integer, explicit units
  provenance_class_commitment
  policy_flags_commitment
  randomness
}
```

`noteCommit = H(domain='TEAPASS_NOTE_V1', chain_id, contract_id, canonical(note))`. Choose a hash supported by the pinned Compact standard library or an audited compatible circuit implementation. Field encoding, bit bounds, domain separation and byte/string canonicalization must be specified in code, **not** guessed.

`nullifier = H(domain='TEAPASS_SPEND_V1', chain_id, contract_id, note_id_random, spend_authority_secret)`. It should be unique and unlinkable to private note details under the chosen threat model. A nullifier does not itself prove ownership; the circuit must establish it from authenticated ownership witnesses, note commitment and valid root membership.

**Public ledger state, conceptual:**

```text
approvedIssuerRoot / approvedIssuerRegistry
knownCommitmentSet or authenticated Merkle root
spentNullifierSet
policyRegistryVersion / allowed operation identifiers
revokedCredentialStatusRoot (if compliance enabled)
```

**Privacy caution:** Putting spent tags and new commitments in the same public transaction may correlate inputs and outputs; the system hides values and, depending on protocol, identities, but does **not** claim complete transaction-graph anonymity.

### 5.3 Actor authorization and issuance

`registerIssuer(issuerAuthority, allowedMaterialClasses, status)` is governance-controlled. Issuer authorization must be cryptographically enforced by the contract, not just an API login. For MVP, approved explicit issuer key/secret proofs are simpler than anonymous membership. Exactly which signature/credential primitive can be efficiently checked in Compact is an implementation spike and must be validated against the pinned toolchain.

`issue(noteCommit, issuerProof, issuanceNonce, policyRef)` checks:
- Issuer is currently authorized for given class and context.
- Proof binds issuer and note commitment to the authorization scope.
- `issuanceNonce` has not been reused by that issuer.
- Public note commitment has not been registered already.
- Issuance is logged with attestation category, date/policy reference and transaction receipt.

**Economic trust boundary:** Valid on-chain issuance attests to a participating issuer's claim, not objective physical quantity. Enforce receiving-party cross-signing and scale reconciliation in pilot design.

### 5.4 Split and blend state transition

Input note set `I`, output note set `O`, authorized transformation operation `op`, private process loss `L` (for allowed operations). For an exact, same-material blending event:

```
Σ qty(inputs) = Σ qty(outputs)
qty(note) in [0, MAX_QTY]
all input notes valid, active, owned/authorized, and unspent
all input notes same permitted material class
all output commitments fresh and well formed
all spent tags unique within tx and globally unspent
```

**Example:** spend 100 kg and 80 kg notes; create 40 kg remainder of A, 40 kg remainder of B and 100 kg blended output. `60 + 40 = 100 kg` is the private blend recipe, while `100 + 80 = 40 + 40 + 100 kg` is the enforced inventory conservation relation. For raw-leaf processing, use `input_mass = saleable_output_mass + declared_waste + justified_loss`, plus permitted yield bounds and material-class conversion policies. Avoid falsely treating green leaf -> manufactured tea as 1:1.

`transform(inputMembershipProofs, authorityWitnesses, privateInputs, privateOutputs, publicTags, outputCommits, operationPolicy)` must atomically:
1. Verify input note commitments belong to current/authorized state.
2. Verify owner/custody authorization and freshness.
3. Reject any previously used nullifier (including duplicated inputs inside one tx).
4. Enforce arithmetic range constraints, no integer overflow/wrap, correct units and rule/operation version.
5. Prove the desired conservation/yield and inherited provenance predicates.
6. Register all nullifiers and new commitments as one valid state transition, or none.

**Privacy versus provenance:** A final output note can inherit a `valid-origin` policy bit only when *every* relevant input note is proven to satisfy the policy, and the circuit binds that predicate to committed outputs. This is an inductive proof about the authenticated digital lineage. Expiration/revocation must be handled in status verification; past satisfied policies may no longer imply present validity.

### 5.5 Transfer and custody

Inventory ownership and physical custody differ. Do not change ownership merely on a QR scan. MVP: receiver and sender co-sign an off-chain custody acceptance bound to a specific note/lot and inventory transfer event, and the authorized owner creates a new note commitment for the receiver where necessary. Pilot: hardware scale and dual confirmation with discrepancy handling. Contract-side ownership transfer is implemented as consume-old-note/create-new-note to avoid mutable private owner state.

### 5.6 Laboratory proof contract module

**P1 after core inventory**; may live in a second contract or module if cross-contract compatibility permits. Enforce binding with an issuance/policy anchor without assuming unrestricted synchronous calls.

Private lab record includes batch binding, lab issuer identity and attestation, analyte, signed measurement (fixed point), unit, sample date, method, policy ID/version and salt. Public verifier should know explicitly: which residue, which threshold, which regulatory standard/time/version and which issuer signed it.

Required predicate:

```
commit(measurement, salt, batchRef, analyte, method, policyId, labId) = existingCommit
lab attestation is authenticated / backed by authorized issued claim
batchRef corresponds to the intended output note/batch
0 <= measurement <= threshold(policyId, analyte, unit, effectiveDate)
policy/credential validity condition holds as of specified verification time
```

If signature verification is too expensive or unsupported in selected Compact version, approved laboratory itself writes an authenticated on-chain commitment through its authorized account/issuer call and proof references that anchored commitment. **Never** accept an arbitrary user-supplied `labVerified=true` boolean as the proof of lab authority. Production deployment must account for the difference between sample batch, tested final lot and the general shipment.

### 5.7 Disclosure model and privacy claims

- **Public:** proof validity, contract/network, receipt, narrow claim, current status, optionally district/coarse region, issuer class, policy version and selected timing metadata.
- **Private to business party:** recipe, precise source identities, private quantity, procurement agreement, proprietary price, full supply relationships.
- **Restricted to auditor:** supporting evidence with consent/authority; cryptographically verifiable document-commitment correspondence and access log.
- **Intentionally visible:** network traffic and transaction timing, possibly counts/links depending on final circuit design; empirical privacy audit required.
- **Not guaranteed:** anonymity across repeated supplier relationships, hiding an unusually distinctive batch size from external operational observations, resistance to colluding physical parties or identification via side-channel data.

### 5.8 Versioning and compatibility spike

The Compact language and Midnight packages evolve. Before implementing, pin **compiler, ledger/runtime, standard library, generated TS bindings, Midnight.js, proof server image and network configuration together** in a `VERSIONS.md` plus lockfile. Compile the smallest proof, run unit tests, deploy to devnet and record working hashes. Do not copy outdated Compact syntax without verifying it. The official docs describe `ledger`, `witness`, `circuit` and explicit public disclosure boundaries.

---

## 6. Operational data model

### 6.1 Minimum relational schema

```sql
actors(id PK, org_id, type, display_name, credential_ref, status, created_at)
organizations(id PK, legal_name, organization_type, region, status)
facilities(id PK, org_id FK, facility_type, geocode_coarse, status)
batches(id PK, external_id, material_class, current_holder_org_id,
        public_alias, status, created_at)
batch_events(id PK, batch_id FK, event_type, actor_id FK, occurred_at,
             recorded_at, event_json, event_signature, prev_event_hash,
             idempotency_key UNIQUE, sync_status)
transforms(id PK, operation_type, output_batch_id FK, policy_id,
           tx_ref, chain_status, created_at)
transform_edges(id PK, transform_id FK, input_batch_id FK,
                output_batch_id FK, private_qty_ref, trace_status)
inventory_notes(id PK, batch_id FK, commitment UNIQUE, owner_org_id,
                nullifier_enc_ref, chain_status, encrypted_note_ref)
lab_attestations(id PK, sample_id, batch_id FK, lab_actor_id FK,
                 analyte_id, method_id, policy_version, commitment,
                 signed_document_ref, validity_status)
verification_claims(id PK, batch_id FK, claim_type, policy_version,
                    proof_tx_ref, last_checked_at, status)
permission_grants(id PK, resource_ref, granted_by, granted_to,
                  access_scope, expires_at, revoked_at)
integration_jobs(id PK, source_system, mapping_version, import_checksum,
                 status, error_report_ref)
```

*Private quantity fields must never be casually exposed through query logs, analytics, debugging interfaces or public API responses. Distinguish private off-chain quantities from ledger commitments and use envelope encryption.*

### 6.2 Event envelope (canonical internal contract)

```json
{
  "schema_version": "1.0",
  "event_id": "evt_001",
  "event_type": "LOT_RECEIVED",
  "batch_ref": "lot_A01",
  "actor_ref": "factory_demo_01",
  "counterparty_ref": "grower_demo_01",
  "occurred_at": "2026-10-19T10:00:00+05:30",
  "idempotency_key": "recv-lot-A01-001",
  "evidence_refs": ["evidence://receipt-001"],
  "previous_event_ref": "evt_000",
  "issuer_signature": "<signature-by-authorized-actor>"
}
```

Example is illustrative, not a real signed event. Version all domain events; generate deterministic canonical serialization for signatures and commitments, and test across TS/Python.

### 6.3 GS1 EPCIS mapping

Use GS1 EPCIS 2.0 as the **interoperability vocabulary**, not as a substitute for PPT. Map ordinary arrival/dispatch to object/transaction events as applicable; map blend/processing to `TransformationEvent`, preserving quantities, event times, business steps, locations and linked transformation IDs. Implement `exportEpcis(batch_id)` and `importEpcis(payload, mappingVersion)` with round-trip fixtures. Treat Tea Board and GTAC integration as unconfirmed until official API access or sandbox specifications are supplied.

---

## 7. API specification (proposed, not deployed)

**Authentication:** JWT session for operator apps plus actor challenge-signature for cryptographically sensitive operations; short-lived roles and org-level authorization. Admin grant is never sufficient to mint on-chain without accepted issuer proof.

| Method | Endpoint | Request / behavior |
|---|---|---|
| `POST` | `/v1/actors` | Admin enrolls demo actor (separate cryptographic issuer approval) |
| `POST` | `/v1/batches` | Create metadata lot and local/offline event |
| `POST` | `/v1/batches/{id}/events` | Append signed event, idempotency key required |
| `POST` | `/v1/issuances/prepare` | Return witness/job inputs, policy and expected commitment |
| `POST` | `/v1/issuances/submit` | Submit signed/proved issuance, return pending chain reference |
| `POST` | `/v1/transforms/prepare` | Validate permissions and compute private transaction draft |
| `POST` | `/v1/transforms/submit` | Submit proven transform transaction; async finality |
| `POST` | `/v1/labs/attestations` | Persist signed lab evidence and commitment |
| `POST` | `/v1/proofs/compliance` | Prove narrowly defined lab predicate for batch and policy |
| `GET` | `/v1/public/batches/{alias}` | Return only public independently checkable claims |
| `GET` | `/v1/private/batches/{id}/lineage` | Role-filtered graph; authenticated only |
| `POST` | `/v1/audit/requests` | Request scoped evidence disclosure |
| `POST` | `/v1/integrations/epcis/import` | Validate EPCIS event payload & mapping |
| `GET` | `/v1/integrations/epcis/export/{id}` | Authorized EPCIS-compatible export |
| `GET` | `/v1/transactions/{txRef}` | Read chain status, finality, errors and explorer URL if available |

**HTTP conventions:** `202 Accepted` for pending proof/tx, `409` duplicate idempotency conflicts/spent note, `422` invalid payload or domain constraints, `403` insufficient role, `503` dependency unavailable. Never return secret witness or plaintext confidential amounts in a public endpoint. Include trace IDs without secrets. Version JSON schema and error codes.

Sample blend **private** request for operator-side local generation:

```json
{
  "operation_id": "blend_demo_001",
  "operation_type": "BLEND",
  "input_note_refs": ["private-note-A", "private-note-B"],
  "outputs": [
    {"kind":"REMAINDER_A","quantity_g":40000},
    {"kind":"REMAINDER_B","quantity_g":40000},
    {"kind":"BLENDED_TEA","quantity_g":100000}
  ],
  "policy_id": "BLEND_MASS_V1"
}
```

**Caution:** This illustrates an authorized private workflow; the operator-side API should be designed so plaintext recipes remain in the client's private execution context rather than transit to the central server. Use one consistent privacy implementation across the real frontend, prover and backend.

---

## 8. Synthetic data and development fixtures

**Availability:** The official NESFIC challenge describes possible access to data, sandboxes, metadata and integration support; it does not promise or publish ready-made private batch records for general applicants. Do not claim government data integration has been validated.

Generate repeatable data with `seed=20261019`, clearly tagged `SYNTHETIC`: 5 growers, 2 facilities, 1 laboratory, 20 leaf lots, 10 manufacturing outputs, 6 auction records, 4 blend outputs and 2 simulated exports. Ground districts/material descriptions in publicly documented examples only where licensing permits; all individual quantities, tests and certificates must be marked fictional.

Fixture folders:

```text
fixtures/
  actors.json
  facilities.json
  green_leaf_lots.csv
  manufacturing_events.jsonl
  lab_results_synthetic.csv
  auction_transactions_synthetic.csv
  blend_recipes_PRIVATE.json
  public_product_passports.json
  epcis_examples/
  adversarial/
    double_spend.json
    forged_issuer.json
    output_inflation.json
    wrong_batch_lab_ref.json
    revoked_credential.json
    duplicate_qr_copy.json
    processing_loss_mismatch.json
```

**Scenario:** Grower A issues 100 kg, B issues 80 kg. An authorized factory produces a 100 kg blend from 60 kg A + 40 kg B and two 40 kg remainders. A synthetic lab record tests the blend against a **demo-only configurable threshold**, not a fabricated claim about the current statutory MRL. Public verification confirms specified claims without revealing recipe, then double-spend and forged compliance attempts fail.

**Data requirements for a genuine pilot:** owner and issuer verification documents; ground-truth event and scale logs; authorized lab results and method; permitted policy tables; real lot transformation IDs; Tea Board/GTAC schemas and access; grower usability feedback; security/privacy rules; field connectivity and costs. Do not create personal profiles from public grower data without lawful basis.

---

## 9. Source code structure and work packages

```text
teapass/
  README.md
  SPEC.md
  VERSIONS.md
  LICENSE-THIRD-PARTY.md
  docker-compose.yml
  .env.example
  apps/
    web/                       # Operator, buyer, auditor, judge interfaces
    api/                       # FastAPI, validation, role-based workflow
  packages/
    protocol/                  # Shared TypeScript types, hash encoding, note schema
    compact-contracts/         # Compact source and generated bindings (build output)
    midnight-client/           # Transaction/wallet/prover providers and typed wrappers
    epcis-adapter/             # EPCIS 2.0 import/export, mapping tests
    data-generator/            # Deterministic synthetic fixtures
  services/
    chain-indexer/             # Chain status and receipt reconciliation
  tests/
    contract/
    property/
    adversarial/
    api/
    e2e/
    privacy/
  fixtures/
  scripts/
    bootstrap-devnet.sh
    seed-demo.sh
    replay-judges.sh
    run-adversarial.sh
  docs/
    THREAT_MODEL.md
    PRIVACY_BOUNDARIES.md
    DEMO_SCRIPT.md
    JUDGES.md
    PROOF.md
    EPCIS_MAPPING.md
    PILOT_ASSUMPTIONS.md
    THIRD_PARTY_ATTRIBUTIONS.md
```

**Code-reuse policy:** review `RaYYeR220/stock-and-foil` and `mr-abims/nightpot` as technique and test-harness references. Both repositories display Apache-2.0 license information at the time of specification; verify the exact files and notices before any copying. Keep `LICENSE`, `NOTICE`, original copyright/license notices and explicit third-party attribution for reused code. Do not submit lightly rebranded prior work; ensure the Midnight-specific material is newly developed or materially extended per current wave rules. Treat GYOTAK's described seafood UI and disclosure ideas as prior art, not freely reusable source code absent a checked license.

---

## 10. Development methodology and milestone plan

Use milestones with measurable gates, not a time-schedule checklist. Dates are indicative and depend on tooling and application rules.

| Phase | Implementation | Definition of done | Dependency |
|---|---|---|---|
| M0: Compatibility spike | Install Compact, pin SDK, run sample private proof and devnet | Compiles and settles one sample tx with saved logs | Compiler/network available |
| M1: Issuance | Implement issuer registry, note commitment and `issue` | Authorized issuance passes; fake/replayed issuance fails | M0 |
| M2: Private inventory | Implement atomic spends, `split`, `transform`, remainder notes, nullifiers | Valid 100+80 -> 40+40+100 passes; double spend/inflation fail | M1 |
| M3: Operational trace | Actor & batch events, signed custody, deterministic graph, PWA skeleton | Can trace a finished lot to recorded root lots and see exceptions | M1 parallel |
| M4: Compliance | Bind signed lab attestation and applicable threshold to output commitment | Valid and invalid signed/test cases differentiate | M2 + M3 |
| M5: Interoperability | EPCIS adapter, CSV/GTAC mock import, QR buyer view | Round-trip fixtures and public verification work | M3 |
| M6: Hardening / showcase | Threat model, negative tests, network receipts, performance bench, video | Reproducible judge replay with actual proof receipt | M2–M5 |
| M7: Pilot design | Field data request, partnership, regulatory mapping and cost study | Validated pilot protocol; no unsupported field claims | Prior phases |

**Parallel tracks:** one agent/developer on Compact, another on API+data graph, another on UI. Avoid coupling core contract compilation to frontend styling. Maintain blocking issues in GitHub and version protocol shapes from the beginning.

### 10.1 First execution instructions for a coding agent

1. Read this spec fully; record any ambiguous cryptographic assumptions in `docs/DECISIONS.md`.
2. Inspect current official Midnight docs and **pin working versions** before writing production protocol code.
3. Implement and run a smallest valid private-amount proof on devnet. Save the known-working sample plus transaction receipt.
4. Implement typed note encoding and domain-separated commitments with deterministic test vectors shared between TS and Python.
5. Add authorized issuance and duplicate issuance negative test. Stop if issuer authority isn't cryptographically enforced.
6. Implement atomic consume-and-create for split/transform, using a bounded number of inputs/outputs for v1. Define maximum arity in config and test overflow/underflow.
7. Add event indexer / transaction reconciliation and Python API.
8. Generate deterministic synthetic data; build private blend screen and public buyer verification view.
9. Implement lab proof after inventory logic is fully tested; do not fake verification behind a badge.
10. Produce `JUDGES.md`, `PROOF.md`, exact commands, tx references and test reports. Label mocked, local and public-network evidence separately.

### 10.2 Recommended implementation simplifications

- MVP maximum: **2–3 input notes, 3–4 output notes**; parameterize limits, extend after benchmarks.
- Use explicit visible issuer identities in P0; anonymous credential membership is P2.
- Use one public compliance policy for P1 demo; versioned multi-jurisdiction rules are P2.
- Use simple encrypted auditor sharing with manual consent in P1; threshold decryption is P2.
- Seed fixed test wallets, isolated proof server and explicit synthetic banners for judge replay.
- Avoid Kafka/Kubernetes; use Docker Compose and an indexer worker until throughput proves a need.

---

## 11. Testing, security, proof of execution and quantitative targets

### 11.1 Mandatory adversarial suite

| ID | Test | Expected behavior |
|---|---|---|
| T01 | Authorized mint with unique nonce | Pass, valid commitment anchored |
| T02 | Unknown issuer tries to mint | Reject on-chain/cryptographically |
| T03 | Same issuance nonce/commitment repeated | Reject |
| T04 | Spend input note twice sequentially | Second transaction rejected |
| T05 | Spend same input twice in one transaction | Reject |
| T06 | Inflate total output quantity | Reject |
| T07 | Negative/overflow/fractional invalid quantity | Reject or fail type/range constraints |
| T08 | Incorrect owner/custody witness | Reject |
| T09 | Wrong Merkle/commitment witness | Reject |
| T10 | Processing conversion violating yield policy | Reject |
| T11 | Valid synthetic lab threshold proof | Pass; reveal no private reading in public response |
| T12 | Test result above threshold | Reject claim proof |
| T13 | Valid lab result attached to wrong batch | Reject |
| T14 | Revoked/expired lab credential | Display invalid/currently untrusted claim under defined rules |
| T15 | Tampered evidence after signing | Signature/commitment mismatch |
| T16 | Replayed offline event / duplicate API operation | Idempotent, no second issuance |
| T17 | Proof submission timeout or chain delay | UI stays pending; safe reconciliation; no double mint |
| T18 | Buyer calls private lineage API | 403; no private information returned |
| T19 | Auditor permission expires | Evidence denied, grant logged |
| T20 | Copy QR to fake physical packet | Demonstrate explicit limitation; no false anti-counterfeit claim |
| T21 | Public chain metadata correlation | Document observable leakage; do not assert complete anonymity |

### 11.2 Performance and operations measurements

Capture actual measurements rather than predeclared success. Target test environment: Mac or Linux developer hardware, local devnet, fixed source revisions. Report median/p95 local proving time, transaction finality time, proof artifact size, memory, network calls, cost if any, transaction throughput and PWA sync time. Goal for demo: all P0 critical tests pass; no claimed real-world throughput until measured. For field validation measure event recording time, error rate, offline queue durability, query latency, cost per batch and ability to complete task on an entry-level Android phone.

### 11.3 Definition of credible evidence

- Git commit/release ID and build lockfiles.
- Compiler and runtime versions.
- Raw test counts, positive and negative results.
- Full command transcript for deploy/verify.
- Local devnet tx hashes and, if available, public testnet tx links.
- Network assertions based on real indexed chain state, not a hardcoded `verified: true`.
- Video recording including failed double-spend and invalid compliance cases.
- Threat model and documented unsupported claims.
- If benchmarking, publish machine specification and repetitions.

### 11.4 Threat mitigations

| Risk | Mitigation |
|---|---|
| Physical-world fabrication | Trusted registered issuers, dual receipt attestation, signed scale records and sampled audits |
| Data leak by API/prover | Encrypt witnesses; participant-controlled/local proving; strict API schemas, no secret logs |
| Commitment guessing | High-entropy salts, domain separation, field-safe encoding, adversarial review |
| Double spends / races | Atomic ledger nullifier state; confirmation-aware API and idempotency keys |
| Colluding institutions | Multi-party custody confirmation and periodic inventory reconciliation; admit limits |
| Credential theft | Rotation, expiry, revocation, limited permissions, secure signer management |
| Temporal compliance error | Policy-effective date, certificate time, explicit current/historical validity semantics |
| Transaction metadata inference | Minimize public metadata, disclosure audit, later batching/traffic analysis research |
| Dependency/toolchain breakage | Version matrix, lockfiles, Docker images, compatibility smoke test in CI |
| Offline records lost | Local encrypted queue, durable status and retry reconciliation; do not treat pending records as on-chain |

---

## 12. User research, pilot and integration plan

### 12.1 Questions for the challenge owner (send before clarification cut-off)

1. Will TRA Tocklai supply anonymized green-leaf receipt, processing, lab and blending records, including source-to-output mappings?
2. Are Tea Board, Chai Sahyog or GTAC export schemas, integration samples and sandbox credentials available to applicants?
3. How does this challenge relate to the C-DAC/AISF/Tea Board/TRA tea traceability initiative announced 21 November 2025, and is the intended deliverable a module or separate platform?
4. Which MRL analytes, test methods and policy authority should a prototype demonstrate?
5. May a prototype use clearly labeled synthetic transactions while showing signed evidence/actual Midnight proofs?
6. What field-level privacy requirements apply to grower identity, geolocation, purchase quantities, lab results and blend ratios?
7. What small-grower devices/connectivity and language requirements apply to pilot users?
8. Which 1–2 supply-chain transitions are most important for pilot validation (garden-to-factory or factory-to-exporter)?

### 12.2 Suggested pilot

Pilot a bounded set of entities (for example one cluster of growers, a bought-leaf factory, a laboratory and one exporter) with partner agreement. Do not promise a particular number of real actors. Conduct initial process observation, shadow capture for one batch lifecycle, data accuracy reconciliation with paper/ERP records, formal consent/security review and a limited live capture. Compare tracking completeness, dispute resolution time, false exceptions, and cost with existing approaches. Co-design with real user workflows.

### 12.3 Prior art and competitive environment

- **C-DAC/AISF/Tea Board/TRA traceability initiative:** Already in progress conceptually; TeaPass should be framed as an interoperable confidential verification module, not a replacement.
- **GS1 EPCIS 2.0:** Existing events and transformation semantics; adopt, do not reinvent.
- **Stock & Foil:** Private commitments and uniqueness, engineering/replay quality reference.
- **NightPot:** Merkle membership and nullifier test patterns; scope differs.
- **GYOTAK/ECOSUS:** Seafood provenance selective disclosure; closest application prior art.
- **Conventional signed event log:** The necessary control architecture and baseline. Benchmark value against it.

**Innovation claim (strict):** not a new ZK proof system, not a new provenance standard, and not new to put origins on a blockchain. The potential innovation is integrating *authenticated cross-organization inventory note transitions, private conservation/processing predicates, batch-bound compliance claims and regulatory/operational disclosure* in an interoperable Assam tea workflow.

---

## 13. Team, resources and indicative cost drivers

**Minimum implementation roles (small team, can overlap):**
- 1 protocol/Compact developer: state semantics, constraints, proof/ledger testing.
- 1 backend/integration developer: API, events, DB, proof orchestration and EPCIS bridge.
- 1 frontend/product developer: grower PWA, factory blending, buyer QR, judge replay.
- Part-time tea-domain mentor/laboratory/regulatory reviewer: policy claims and physical workflows.
- Part-time security reviewer before pilot: private-state, issuer, prover and key management.

**Local build:** developer Mac/Linux machine, Docker, Node toolchain, Python, Postgres and devnet. GPU not required for baseline concept; actual proving cost depends on circuits and environment. **Cost drivers** include hosted API/database, encrypted storage, SMS/communications, proof generation compute, field-device support, partner onboarding, expert compliance review and audit. Benchmark before estimating a scale-up grant budget. No on-chain fee estimate should be invented without testing the actual target environment.

**Budget framing (illustrative, to be replaced with quotes):** prototype costs dominated by development time; demonstration infrastructure likely modest. Pilot budget requires staffing, field training, secure devices, travel/site visits, partner testing, audit and longer-running infrastructure. Separate funded government pilot costs from AKINDO work.

---

## 14. Judge walkthrough — exactly what to demonstrate

**Preparation:** Start from deterministic fixtures; show devnet configuration, compiler version, test suite status and evidence that the displayed interface is actually calling real Compact-generated contracts.

**0:00–0:25 Problem:** Assam tea crosses growers, factories, blenders and buyers. Supply-chain proofs require confidentiality.

**0:25–0:55 Root issuance:** Attested Grower A 100 kg and Grower B 80 kg notes are committed; show authorized actor and receipts.

**0:55–1:45 Private blend:** Operator selects 60 kg A + 40 kg B, generates proof, consumes two original notes, obtains 40 kg A remainder, 40 kg B remainder and 100 kg blend note. Show transaction receipt and confirm actual state.

**1:45–2:15 Public buyer:** Open QR. Buyer sees valid provenance/inventory claim, policy name, proof receipt and the fact that supplier list/recipe are not disclosed. Distinguish an issued assertion from independently observed physical proof.

**2:15–2:45 Negative test:** Attempt to re-spend source note; contract rejects. Optionally attempt output inflation or forged issuer; show genuine error response.

**2:45–3:15 Lab proof:** Valid policy-specific synthetic lab attestation satisfies configured threshold; altered result or wrong batch fails. If not implemented yet, label as roadmap, never simulate as a live proof.

**3:15–3:35 Interoperability:** Export transformation to EPCIS-style payload and show how a partner adapter would ingest official batch exports if granted.

**3:35–4:00 Conclusion:** Transparent limitations and pilot request: partner data, registered labs, permitted regulatory mappings and real physical-process integration.

---

## 15. Milestone acceptance: launch / no-launch criteria

### AKINDO submission: GO only if

- Real, newly built/materially extended Compact functionality compiles and runs in a reproducible environment.
- At least one critical rule is enforced by cryptography and on-chain state rather than a mocked backend boolean.
- Valid flow and adversarial failures demonstrated with receipts, source and tests.
- Reused source is lawfully attributed and wave eligibility confirmed.
- Public/privacy disclosures match demonstrated guarantees; no false assertions.

### NESFIC development proposal: GO only if

- Covers complete target process in design even if the MVP demos a bounded slice.
- All 12 official proposal sections are present.
- Interoperability and offline plan are realistic; any missing API/data access is explicitly stated.
- Pilot, actor authorization and actual source-data trust boundary are addressed.
- Innovation is specific, technically defensible and complementary to existing work.
- Development readiness, team capabilities, milestones and risks are credible.

### STOP / change scope if

- The supported Midnight toolchain cannot handle our proposed note state/verification efficiently enough for a practical demo: reduce arity and show one meaningful predicate instead.
- The contract does not enforce uniqueness/issuer authorization itself: do not market it as solving double consumption or forged source.
- The physical provenance model cannot identify credible attestors: frame as workflow verification, not verified authentic Assam origin.
- The buyer view leaks private data or has hardcoded `verified` badges: stop and correct before submission.
- A conventional trust-sharing arrangement solves the target customer's issue more simply: reconsider whether Midnight adds enough value.

---

## 16. Appendix: official and technical references

1. NESFIC I-08 official challenge: https://startup.assam.gov.in/nesfic26/problem-statements/nesfic-i-08
2. NESFIC uniform proposal requirements (12 required components): https://startup.assam.gov.in/nesfic26/docs/uspr.pdf
3. C-DAC's 2025 Assam tea blockchain initiative: https://www.cdac.in/index.aspx?id=lu_QS-BBTTS
4. Midnight official Compact documentation: https://docs.midnight.network/compact
5. Midnight local private smart contract guide: https://docs.midnight.network/guides/build-a-private-smart-contract
6. Midnight deployment guide: https://docs.midnight.network/guides/deploy-and-operate
7. GS1 EPCIS 2.0.1 TransformationEvent specification: https://ref.gs1.org/standards/epcis/2.0.1/
8. Stock & Foil repository: https://github.com/RaYYeR220/stock-and-foil
9. NightPot repository: https://github.com/mr-abims/nightpot
10. AKINDO Midnight buildathon landing page: https://app.akindo.io/wave-hacks/jaMZjqPOBsLXvjdG
11. Tea Board India: https://www.teaboard.gov.in/

**Source-control note:** This is a product/technical design specification, not a verified fact that the contracts are implemented or compatible. The coding agent must create a version-locked compatibility proof and record test evidence before upgrading any design claim to `implemented`.

---

## 17. Open decisions for the engineering kickoff

| ID | Decision | Default recommendation | Resolution artifact |
|---|---|---|---|
| D1 | Exact proof/contract target versions | Pin first fully working compatible set | `VERSIONS.md` + smoke test |
| D2 | Note hash / encoding | Versioned, domain-separated compatible circuit hash | test vectors |
| D3 | Authorized issuer verification | Explicit on-chain issuer authority for MVP | forged issuer negative test |
| D4 | Multi-input arity | 2 inputs and 3 outputs minimum; bounded extension | contract benchmark |
| D5 | Cross-organization transfer | Consume-and-create + dual signed custody event | custody scenario |
| D6 | Lab certificate authority | Lab-authorized anchored commitment if in-circuit signature infeasible | compliance negative tests |
| D7 | Prover locality | Local/client-controlled for P0/P1, never untrusted shared service | security assessment |
| D8 | Batch/QR identity | Batch-level alias first, unique pack serial later | threat model |
| D9 | Institutional API import | EPCIS + CSV mocks until documentation granted | adapter tests |
| D10 | Privacy guarantee | Confidential quantities/recipe; **no** full graph anonymity claim | privacy analysis |

**End of specification.**
