import base64
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EncryptedPayload(StrictModel):
    # Participant performs encryption and retains keys; server never decrypts.
    algorithm: Literal["A256GCM"]
    key_id: UUID
    nonce: str
    ciphertext: str = Field(min_length=24, max_length=87384)

    @field_validator("nonce")
    @classmethod
    def nonce_length(cls, value: str):
        if len(base64.b64decode(value, validate=True)) != 12:
            raise ValueError("Expected a base64-encoded 12-byte GCM nonce")
        return value

    @field_validator("ciphertext")
    @classmethod
    def valid_ciphertext(cls, value: str):
        if not 16 <= len(base64.b64decode(value, validate=True)) <= 65536:
            raise ValueError("Ciphertext must include the authentication tag and be <= 64 KiB")
        return value


class Command(StrictModel):
    schema_version: Literal["1.0"]
    deployment_id: str = Field(min_length=1, max_length=100)
    actor_id: UUID
    org_id: UUID
    operation_id: UUID
    batch_id: UUID
    occurred_at: AwareDatetime
    encrypted_payload: EncryptedPayload | None = None

    @field_validator("occurred_at")
    @classmethod
    def normalize_time(cls, value: datetime):
        return value.astimezone(UTC)


class CreateBatchCommand(Command):
    command_type: Literal["CREATE_BATCH"]
    external_id: str = Field(min_length=1, max_length=100)
    public_alias: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{7,99}$")
    material_class: Literal["GREEN_LEAF", "MADE_TEA", "BLENDED_TEA"]
    published: bool = False
    synthetic: bool


class AppendEventCommand(Command):
    command_type: Literal["APPEND_EVENT"]
    event_type: Literal["OBSERVATION_RECORDED", "CORRECTION_RECORDED"]
    previous_event_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    supersedes_event_id: UUID | None = None


class SignedBatch(StrictModel):
    command: CreateBatchCommand
    signature: str = Field(min_length=88, max_length=88)


class SignedEvent(StrictModel):
    command: AppendEventCommand
    signature: str = Field(min_length=88, max_length=88)


class ActorEnrollment(StrictModel):
    subject: str = Field(min_length=1, max_length=255)
    role: Literal["grower", "factory", "lab", "blender", "buyer", "auditor"]
    signing_public_key: str = Field(min_length=44, max_length=44)

    @field_validator("signing_public_key")
    @classmethod
    def valid_key(cls, value: str):
        if len(base64.b64decode(value, validate=True)) != 32:
            raise ValueError("Expected base64-encoded Ed25519 public key")
        return value


class CommandResult(StrictModel):
    batch_id: UUID
    event_id: UUID
    event_hash: str
    sequence: int
    status: Literal["RECORDED"] = "RECORDED"


class PublicBatch(StrictModel):
    public_alias: str
    material_class: str
    synthetic: bool
    status: Literal["RECORDED"] = "RECORDED"
    verification_status: Literal[
        "NOT_VERIFIED", "VERIFIED_CLAIMS", "INVALID_CLAIMS", "UNAVAILABLE"
    ] = "NOT_VERIFIED"
    claims: list[dict] = Field(default_factory=list)
    chain_receipt: None = None
    checked_at: datetime
    limitations: list[str]
