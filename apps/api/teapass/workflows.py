from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select

from teapass.ledger import append_event, head_event, owned_batch, reserve_operation
from teapass.models import Actor, Batch, BatchEvent, Organization
from teapass.security import verify_command
from teapass.workflow_models import (
    ChainJob,
    Custody,
    LabAttestation,
    PermissionGrant,
    TransformEdge,
)
from teapass.workflow_schemas import (
    AttestLab,
    CustodyOffer,
    CustodyResponse,
    GrantEvidence,
    PrepareChain,
    RevokeGrant,
    SubmitChain,
)


def active_actor(db, actor_id):
    actor = db.scalar(
        select(Actor)
        .join(Organization)
        .where(Actor.id == actor_id, Actor.active.is_(True), Organization.active.is_(True))
    )
    if actor is None:
        raise HTTPException(422, "RECIPIENT_UNAVAILABLE")
    return actor


def valid_expiry(expiry, maximum_days=30):
    if not datetime.now(UTC) < expiry <= datetime.now(UTC) + timedelta(days=maximum_days):
        raise HTTPException(422, "INVALID_EXPIRY")


def grant_for(db, actor, batch_id, scope):
    return db.scalar(
        select(PermissionGrant)
        .where(
            PermissionGrant.batch_id == batch_id,
            PermissionGrant.granted_to == actor.id,
            PermissionGrant.scope == scope,
            PermissionGrant.revoked_at.is_(None),
            PermissionGrant.expires_at > datetime.now(UTC),
        )
        .with_for_update()
    )


def execute_workflow(db, body, actor, settings, idempotency_key):
    c = body.command
    verify_command(c, body.signature, actor, settings)
    record, prior = reserve_operation(
        db, actor.id, idempotency_key, "/v1/workflows", body.model_dump(mode="json")
    )
    if prior:
        return prior
    # Lock batch first across all workflow paths to serialize head and custody transitions.
    batch = db.scalar(select(Batch).where(Batch.id == c.batch_id).with_for_update())
    if batch is None:
        raise HTTPException(404, "BATCH_NOT_FOUND")
    owner = batch.org_id == actor.org_id and actor.role in {"admin", "grower", "factory", "blender"}
    transfer = None
    if isinstance(c, CustodyResponse):
        transfer = db.scalar(
            select(Custody)
            .where(
                Custody.id == c.transfer_id,
                Custody.batch_id == batch.id,
                Custody.receiver_id == actor.id,
            )
            .with_for_update()
        )
        if transfer is None:
            raise HTTPException(404, "CUSTODY_OFFER_NOT_FOUND")
        if transfer.status != "OFFERED" or transfer.expires_at <= datetime.now(UTC):
            raise HTTPException(409, "CUSTODY_OFFER_CLOSED")
        offer = db.get(BatchEvent, transfer.offer_event_id)
        if offer.event_hash != c.offer_event_hash:
            raise HTTPException(422, "CUSTODY_OFFER_BINDING_MISMATCH")
    elif isinstance(c, AttestLab):
        if actor.role != "lab" or not grant_for(db, actor, batch.id, "lab_attest"):
            raise HTTPException(403, "LAB_GRANT_REQUIRED")
    elif isinstance(c, PrepareChain) and c.operation == "anchorLab":
        if actor.role != "lab" or not grant_for(db, actor, batch.id, "lab_attest"):
            raise HTTPException(403, "LAB_GRANT_REQUIRED")
    elif isinstance(c, SubmitChain) and actor.role == "lab":
        job = db.scalar(
            select(ChainJob).where(
                ChainJob.id == c.job_id,
                ChainJob.actor_id == actor.id,
                ChainJob.batch_id == batch.id,
                ChainJob.operation == "anchorLab",
            )
        )
        if job is None or not grant_for(db, actor, batch.id, "lab_attest"):
            raise HTTPException(403, "LAB_GRANT_REQUIRED")
    elif not owner:
        raise HTTPException(404, "BATCH_NOT_FOUND")
    previous = head_event(db, batch.id)
    if previous is None or c.previous_event_hash != previous.event_hash:
        raise HTTPException(409, "STALE_EVENT_PARENT")

    if isinstance(c, CustodyOffer):
        valid_expiry(c.expires_at, 7)
        recipient = active_actor(db, c.receiver_id)
        if recipient.id == actor.id or recipient.role not in {
            "grower",
            "factory",
            "blender",
            "buyer",
        }:
            raise HTTPException(422, "INVALID_CUSTODY_RECIPIENT")
        # Expired offers do not permanently block new handovers.
        for old in db.scalars(
            select(Custody).where(Custody.batch_id == batch.id, Custody.status == "OFFERED")
        ).all():
            if old.expires_at <= datetime.now(UTC):
                old.status = "EXPIRED"
        db.flush()
        if db.scalar(
            select(Custody).where(Custody.batch_id == batch.id, Custody.status == "OFFERED")
        ):
            raise HTTPException(409, "CUSTODY_OFFER_PENDING")
    elif isinstance(c, GrantEvidence):
        valid_expiry(c.expires_at)
        recipient = active_actor(db, c.recipient_id)
        if recipient.role != ("auditor" if c.scope == "events" else "lab"):
            raise HTTPException(422, "GRANT_ROLE_MISMATCH")
    elif isinstance(c, RevokeGrant):
        grant = db.scalar(
            select(PermissionGrant)
            .where(PermissionGrant.id == c.grant_id, PermissionGrant.batch_id == batch.id)
            .with_for_update()
        )
        if grant is None:
            raise HTTPException(404, "GRANT_NOT_FOUND")
        grant.revoked_at = datetime.now(UTC)
    elif isinstance(c, AttestLab):
        valid_expiry(c.expires_at, 365)
    elif isinstance(c, PrepareChain):
        if not settings.midnight_contract_address:
            raise HTTPException(503, "MIDNIGHT_NOT_CONFIGURED")
        if len(set(c.output_commitments)) != len(c.output_commitments):
            raise HTTPException(422, "DUPLICATE_OUTPUT_COMMITMENT")
        arity = {
            "issue": 0,
            "transfer": 1,
            "split": 1,
            "blend": 2,
            "process": 1,
            "proveCompliance": 0,
            "anchorLab": 0,
        }[c.operation]
        if len(c.input_batch_ids) != arity or len(set(c.input_batch_ids)) != arity:
            raise HTTPException(422, "INVALID_INPUT_ARITY")
        outputs = {
            "issue": 1,
            "transfer": 1,
            "split": 2,
            "blend": 3,
            "process": 1,
            "proveCompliance": 1,
            "anchorLab": 1,
        }[c.operation]
        if len(c.output_commitments) != outputs:
            raise HTTPException(422, "INVALID_OUTPUT_ARITY")
        for source in sorted(c.input_batch_ids):
            owned_batch(db, source, actor)
        if batch.id in c.input_batch_ids:
            raise HTTPException(422, "OUTPUT_BATCH_MUST_BE_NEW")
    elif isinstance(c, SubmitChain):
        job = db.scalar(
            select(ChainJob)
            .where(
                ChainJob.id == c.job_id,
                ChainJob.actor_id == actor.id,
                ChainJob.batch_id == batch.id,
            )
            .with_for_update()
        )
        if job is None:
            raise HTTPException(404, "CHAIN_JOB_NOT_FOUND")
        if job.status != "PREPARED":
            raise HTTPException(409, "CHAIN_JOB_ALREADY_SUBMITTED")
        job.tx_id, job.status = c.tx_id, "SUBMITTED"

    result = append_event(db, c, body.signature, actor, c.command_type, previous)
    if isinstance(c, CustodyOffer):
        db.add(
            Custody(
                id=c.transfer_id,
                batch_id=batch.id,
                sender_id=actor.id,
                receiver_id=c.receiver_id,
                offer_event_id=c.operation_id,
                expires_at=c.expires_at,
            )
        )
    elif isinstance(c, CustodyResponse):
        transfer.response_event_id, transfer.status = c.operation_id, c.decision
    elif isinstance(c, GrantEvidence):
        db.add(
            PermissionGrant(
                id=c.grant_id,
                batch_id=batch.id,
                granted_by=actor.id,
                granted_to=c.recipient_id,
                scope=c.scope,
                expires_at=c.expires_at,
                key_envelope=c.key_envelope.model_dump(mode="json"),
                event_id=c.operation_id,
            )
        )
    elif isinstance(c, AttestLab):
        db.add(
            LabAttestation(
                id=c.attestation_id,
                batch_id=batch.id,
                lab_actor_id=actor.id,
                event_id=c.operation_id,
                commitment=c.commitment,
                policy_id=c.policy_id,
                expires_at=c.expires_at,
            )
        )
    elif isinstance(c, PrepareChain):
        db.add(
            ChainJob(
                id=c.job_id,
                batch_id=batch.id,
                actor_id=actor.id,
                operation=c.operation,
                network=settings.midnight_network,
                contract_address=settings.midnight_contract_address,
                intent=c.model_dump(mode="json"),
            )
        )
        db.flush()
        for source in c.input_batch_ids:
            db.add(TransformEdge(job_id=c.job_id, input_batch_id=source, output_batch_id=batch.id))
    db.flush()
    record.response, record.status_code = result, 201
    return result
