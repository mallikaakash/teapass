# Privacy and trust boundaries

The Compact contract hides note amounts, salts, owner secret material, lab readings and the private blend recipe. Public commitment membership lookups and transaction timing expose links; this implementation does not claim anonymous supply graphs. Issuer/lab authority keys, approved policies, nullifiers, commitments, domain-bound batch references, material classes and compliance claim metadata are public. Batch references use SHA-256 over the deployment ID and normalized batch UUID; they bind metadata but are not encryption or anonymity.

Operational event signatures prove possession of enrolled Ed25519 keys and bind deployment, actor, organization, batch, operation and previous event. They do not establish physical origin, honest weighing, sample identity, statutory compliance or ownership on Midnight. Custody offers and responses are separate signed assertions, not an inventory ownership change.

API encrypted envelopes are opaque. Participant helpers use AES-256-GCM with random 12-byte nonces and context-bound associated data. Never put amounts, exact supplier identities, recipes or locations into public aliases/external IDs. A public alias is opt-in but still correlates business activity.

For explicit auditor sharing, use a shareable AES data key and wrap it to the recipient's X25519 public key with HKDF-SHA256 and AES-GCM. The envelope binds key ID, recipient key, ephemeral key and deployment/batch/grant context. The receiver obtains a nonextractable decrypt-only key. Signing keys remain nonextractable. Recipient public keys must be authenticated out of band until the enrollment UI/vault supports them; never trust a key pasted by an unauthenticated party. Store data keys only in the participant vault or wrapped backups, never server plaintext.

Grant expiry/revocation stops future API disclosure. It cannot erase keys or evidence already downloaded by an auditor. Successful disclosures are logged in an append-only table. Denied disclosures are not currently persisted as audit rows because request transactions roll back on denial; centralized security-event monitoring remains a release prerequisite.

The central API accepts only encrypted operational data and public intent/receipt metadata. Proving in this implementation is local to the participant/test harness. Sending witness-bearing proof requests to an untrusted remote prover would break this boundary. Never reuse the public local genesis seed on a public network.

The verifier trusts the configured node/indexer, checks canonical finality and exact compiled verifier keys, and exposes that trust basis in the response. It is not a light client proving consensus independently. Current revocation/expiry can invalidate trust in a historical proof without invalidating that historical transaction.
