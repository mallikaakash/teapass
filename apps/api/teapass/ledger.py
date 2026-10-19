from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from teapass.models import Actor, Batch, BatchEvent, IdempotencyRecord
from teapass.schemas import Command, CommandResult
from teapass.security import digest


def reserve_operation(db: Session, actor_id: UUID, key: str, route: str, body: dict):
    fingerprint = digest({"route": route, "body": body})
    # PostgreSQL waits for conflicting transactions. The stored response and domain write
    # commit together; a failed request rolls back the reservation as well.
    inserted = db.execute(
        insert(IdempotencyRecord)
        .values(
            actor_id=actor_id,
            key=key,
            request_hash=fingerprint,
        )
        .on_conflict_do_nothing()
        .returning(IdempotencyRecord.key)
    ).scalar_one_or_none()
    record = db.get(IdempotencyRecord, (actor_id, key))
    if inserted is None:
        if record.request_hash != fingerprint:
            raise HTTPException(409, "IDEMPOTENCY_KEY_REUSED")
        if record.response is None:
            raise HTTPException(409, "OPERATION_IN_PROGRESS")
        return record, record.response
    return record, None


def owned_batch(db: Session, batch_id: UUID, actor: Actor, *, lock: bool = False):
    query = select(Batch).where(Batch.id == batch_id, Batch.org_id == actor.org_id)
    if lock:
        query = query.with_for_update()
    batch = db.scalar(query)
    if batch is None:
        raise HTTPException(404, "BATCH_NOT_FOUND")
    return batch


def head_event(db: Session, batch_id: UUID):
    return db.scalar(
        select(BatchEvent)
        .where(BatchEvent.batch_id == batch_id)
        .order_by(BatchEvent.sequence.desc())
        .limit(1)
    )


def append_event(
    db: Session,
    command: Command,
    signature: str,
    actor: Actor,
    event_type: str,
    previous: BatchEvent | None,
):
    sequence = 1 if previous is None else previous.sequence + 1
    previous_hash = None if previous is None else previous.event_hash
    payload = command.model_dump(mode="json")
    event_hash = digest(
        {
            "domain": "TEAPASS_EVENT_V1",
            "command": payload,
            "signature": signature,
            "previous_event_hash": previous_hash,
            "sequence": sequence,
        }
    )
    db.add(
        BatchEvent(
            id=command.operation_id,
            batch_id=command.batch_id,
            actor_id=actor.id,
            sequence=sequence,
            event_type=event_type,
            signed_command=payload,
            signature=signature,
            signing_public_key=actor.signing_public_key,
            previous_event_hash=previous_hash,
            event_hash=event_hash,
            occurred_at=command.occurred_at,
        )
    )
    db.flush()
    return CommandResult(
        batch_id=command.batch_id,
        event_id=command.operation_id,
        event_hash=event_hash,
        sequence=sequence,
    ).model_dump(mode="json")


def event_view(event: BatchEvent):
    import base64

    return {
        "event_id": str(event.id),
        "sequence": event.sequence,
        "command": event.signed_command,
        "signature": event.signature,
        "signing_public_key": base64.b64encode(event.signing_public_key).decode(),
        "previous_event_hash": event.previous_event_hash,
        "event_hash": event.event_hash,
        "recorded_at": datetime.isoformat(event.recorded_at),
    }
