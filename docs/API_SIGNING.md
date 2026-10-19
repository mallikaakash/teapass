# Operational command signatures v1

These signatures authenticate off-chain submissions. They do not authorize Compact issuance or replace on-chain proofs.

1. Build the typed command using the OpenAPI schema. Unknown fields are rejected.
2. Normalize UUIDs to lowercase hyphenated strings and `occurred_at` to UTC ISO 8601 ending `Z`; use six fractional digits when microseconds are nonzero. Include all default/nullable fields exactly as the server model emits: batch creation includes `encrypted_payload: null` when absent and `published: false` when omitted; append includes `encrypted_payload: null` and `supersedes_event_id: null` when absent. Prefer sending these explicitly.
3. Serialize the normalized command using RFC 8785 JSON Canonicalization Scheme (JCS), UTF-8. This is not arbitrary `JSON.stringify` order. No floating-point mass fields are accepted.
4. Sign `UTF8("TEAPASS_OPERATION_V1") || 0x00 || canonical_command_bytes` using the enrolled actor's Ed25519 key.
5. Encode the 64-byte signature using standard padded base64. POST `{ "command": ..., "signature": ... }` with a bearer token and an `Idempotency-Key` of 8–100 ASCII letters/digits/underscore/hyphen.

The command binds deployment, actor, org, batch, operation ID and occurrence time. Batch creation also binds publication consent. Appends bind the previous event hash, preventing history forks. There is no maximum offline age; timestamps more than five minutes in the future are rejected. `recorded_at` is the database receipt time, not the actor's claimed occurrence time.

Identical retries return the original response. Reusing a key with a different typed request or route returns 409. Reusing an operation UUID under another retry key also returns 409. A stale append returns `STALE_EVENT_PARENT`; fetch the latest authorized event head, review the conflict, and create/sign a new operation. Never silently rebase a participant signature.

The event digest is SHA-256 of RFC 8785 encoding of:

```json
{
  "domain": "TEAPASS_EVENT_V1",
  "command": "<full normalized command object>",
  "signature": "<base64 actor signature>",
  "previous_event_hash": "<previous digest or null for creation>",
  "sequence": 1
}
```

`command` above denotes an object, not an actual string. Authorized event reads return the normalized signed command and the signing public key snapshot so historical signatures can be checked. A server-assigned sequence and database receipt time do not independently prove physical chronology. A database owner can bypass triggers; external anchoring and operational access controls are separate release gates.

Private payloads must be encrypted on a participant-controlled client using AES-256-GCM with a fresh 12-byte nonce per key, associated data binding the deployment/org/batch/operation, and an authentication tag appended to ciphertext. The server checks base64 encoding and lengths; it cannot prove correct encryption, nonce uniqueness, or possession of the encryption key. The WebCrypto client encryptor is implemented in `packages/client-sdk`. Participant encryption-key distribution and recovery still need a complete enrollment flow. Signing-key rotation is a separate audited admin workflow. Do not put recipes, quantities, exact locations, personal data or evidence content in external IDs or public aliases.


## Extended workflows

`POST /v1/workflows` accepts discriminated signed commands: OFFER_CUSTODY, RESPOND_CUSTODY, GRANT_EVIDENCE, REVOKE_GRANT, ATTEST_LAB, PREPARE_CHAIN and SUBMIT_CHAIN. All include the current `previous_event_hash`. The custody receiver signs the exact offer hash, transfer ID, batch and response decision; acceptance leaves Compact ownership unchanged. An audit grant is recipient-, batch-, scope- and expiry-bound. Lab evidence requires a separate `lab_attest` grant.

Use `packages/client-sdk`'s `normalizeCommand` before `signCommand` for default fields, UUID casing and timestamp formatting. Private values must already be encrypted; never send recipes to obtain a signature. Store nonextractable CryptoKeys in a participant-controlled vault. This helper is not a completed device recovery or recipient key-delivery system.

`POST /v1/actors/lifecycle` uses MANAGE_ACTOR with ROTATE_KEY or SET_ACTIVE. Admin changes require the existing admin's signature. Rotation additionally requires the new target key's signature over `TEAPASS_KEY_POSSESSION_V1\0 || command_bytes(command)`. This proves possession of the new key; institutional approval is still an operational responsibility.
