import base64
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, TypeAdapter, field_validator

from teapass.schemas import Command, EncryptedPayload, StrictModel

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class WorkflowCommand(Command):
    previous_event_hash: Hash


class CustodyOffer(WorkflowCommand):
    command_type: Literal["OFFER_CUSTODY"]
    transfer_id: UUID
    receiver_id: UUID
    expires_at: AwareDatetime
    note_commitment: Hash
    # Optional chain transfer reference is a declaration, never proof of ownership.
    inventory_tx_id: Hash | None = None


class CustodyResponse(WorkflowCommand):
    command_type: Literal["RESPOND_CUSTODY"]
    transfer_id: UUID
    offer_event_hash: Hash
    decision: Literal["ACCEPTED", "REJECTED", "DISCREPANCY"]


class RecipientKeyEnvelope(EncryptedPayload):
    algorithm: Literal["X25519-HKDF-SHA256-A256GCM"]
    ephemeral_public_key: str = Field(min_length=44, max_length=44)

    @field_validator("ephemeral_public_key")
    @classmethod
    def valid_ephemeral_key(cls, value):
        if len(base64.b64decode(value, validate=True)) != 32:
            raise ValueError("Expected 32-byte X25519 public key")
        return value

    @field_validator("ciphertext")
    @classmethod
    def wrapped_key_length(cls, value):
        if len(base64.b64decode(value, validate=True)) != 48:
            raise ValueError("Expected wrapped 32-byte AES key and tag")
        return value


class GrantEvidence(WorkflowCommand):
    command_type: Literal["GRANT_EVIDENCE"]
    grant_id: UUID
    recipient_id: UUID
    scope: Literal["events", "lab_attest"]
    expires_at: AwareDatetime
    key_envelope: RecipientKeyEnvelope


class RevokeGrant(WorkflowCommand):
    command_type: Literal["REVOKE_GRANT"]
    grant_id: UUID


class AttestLab(WorkflowCommand):
    command_type: Literal["ATTEST_LAB"]
    attestation_id: UUID
    commitment: Hash
    policy_id: Hash
    expires_at: AwareDatetime
    encrypted_payload: EncryptedPayload


class PrepareChain(WorkflowCommand):
    command_type: Literal["PREPARE_CHAIN"]
    job_id: UUID
    operation: Literal[
        "issue", "transfer", "split", "blend", "process", "proveCompliance", "anchorLab"
    ]
    input_batch_ids: list[UUID] = Field(default_factory=list, max_length=2)
    output_commitments: list[Hash] = Field(min_length=1, max_length=3)
    encrypted_payload: EncryptedPayload


class SubmitChain(WorkflowCommand):
    command_type: Literal["SUBMIT_CHAIN"]
    job_id: UUID
    tx_id: Hash


Workflow = Annotated[
    CustodyOffer
    | CustodyResponse
    | GrantEvidence
    | RevokeGrant
    | AttestLab
    | PrepareChain
    | SubmitChain,
    Field(discriminator="command_type"),
]
workflow_adapter = TypeAdapter(Workflow)


class SignedWorkflow(StrictModel):
    command: Workflow
    signature: str = Field(min_length=88, max_length=88)
