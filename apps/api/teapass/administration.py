import base64
from datetime import UTC
from typing import Literal
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException
from pydantic import AwareDatetime, Field, field_validator, model_validator
from sqlalchemy import select

from teapass.ledger import reserve_operation
from teapass.models import Actor
from teapass.schemas import ActorEnrollment, StrictModel
from teapass.security import command_bytes, verify_command
from teapass.workflow_models import AdministrationEvent


class ActorCommand(StrictModel):
    schema_version: Literal["1.0"]
    deployment_id: str = Field(min_length=1, max_length=100)
    actor_id: UUID
    org_id: UUID
    operation_id: UUID
    occurred_at: AwareDatetime
    command_type: Literal["MANAGE_ACTOR"]
    target_id: UUID
    action: Literal["ROTATE_KEY", "SET_ACTIVE"]
    new_public_key: str | None = None
    active: bool | None = None

    @field_validator("occurred_at")
    @classmethod
    def normalize_time(cls, value):
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def action_fields(self):
        if self.action == "ROTATE_KEY":
            if not self.new_public_key or self.active is not None:
                raise ValueError("Rotation needs only a new public key")
            ActorEnrollment.valid_key(self.new_public_key)
        elif self.active is None or self.new_public_key is not None:
            raise ValueError("Status change needs only active flag")
        return self


class SignedActorCommand(StrictModel):
    command: ActorCommand
    signature: str = Field(min_length=88, max_length=88)
    new_key_proof: str | None = Field(default=None, min_length=88, max_length=88)


def manage_actor(db, body, actor, settings, key):
    if actor.role != "admin":
        raise HTTPException(403, "ADMIN_ROLE_REQUIRED")
    c = body.command
    verify_command(c, body.signature, actor, settings)
    record, prior = reserve_operation(
        db, actor.id, key, "/v1/actors/lifecycle", body.model_dump(mode="json")
    )
    if prior:
        return prior
    # Non-admin targets avoid multi-admin row-lock cycles.
    # Admin recovery remains an offline ceremony.
    target = db.scalar(
        select(Actor)
        .where(Actor.id == c.target_id, Actor.org_id == actor.org_id, Actor.role != "admin")
        .with_for_update()
    )
    if target is None:
        raise HTTPException(404, "MANAGEABLE_ACTOR_NOT_FOUND")
    if c.action == "ROTATE_KEY":
        new_key = base64.b64decode(c.new_public_key, validate=True)
        try:
            Ed25519PublicKey.from_public_bytes(new_key).verify(
                base64.b64decode(body.new_key_proof or "", validate=True),
                b"TEAPASS_KEY_POSSESSION_V1\x00" + command_bytes(c),
            )
        except (ValueError, InvalidSignature):
            raise HTTPException(403, "NEW_KEY_PROOF_REQUIRED") from None
        target.signing_public_key = new_key
    else:
        if body.new_key_proof is not None:
            raise HTTPException(422, "UNEXPECTED_NEW_KEY_PROOF")
        target.active = c.active
    db.add(
        AdministrationEvent(
            id=c.operation_id,
            actor_id=actor.id,
            org_id=actor.org_id,
            target_id=target.id,
            action=c.action,
            command=c.model_dump(mode="json"),
            signature=body.signature,
            signing_public_key=actor.signing_public_key,
        )
    )
    db.flush()
    result = {"actor_id": str(target.id), "active": target.active, "action": c.action}
    record.response, record.status_code = result, 200
    return result
