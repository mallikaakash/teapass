"""Durable workflow projections. Original signed events remain the source of evidence."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from teapass.models import Base


class Custody(Base):
    __tablename__ = "custody_transfers"
    __table_args__ = (
        Index(
            "one_pending_custody_per_batch",
            "batch_id",
            unique=True,
            postgresql_where=text("status = 'OFFERED'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"), index=True)
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    receiver_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    offer_event_id: Mapped[UUID] = mapped_column(ForeignKey("batch_events.id"))
    response_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("batch_events.id"))
    status: Mapped[str] = mapped_column(String(20), default="OFFERED")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PermissionGrant(Base):
    __tablename__ = "permission_grants"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"), index=True)
    granted_by: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    granted_to: Mapped[UUID] = mapped_column(ForeignKey("actors.id"), index=True)
    scope: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Encrypted by the participant for the recipient; never a plaintext data key.
    key_envelope: Mapped[dict] = mapped_column(JSONB)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("batch_events.id"))


class AccessLog(Base):
    __tablename__ = "access_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    grant_id: Mapped[UUID] = mapped_column(ForeignKey("permission_grants.id"))
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"))
    action: Mapped[str] = mapped_column(String(40))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LabAttestation(Base):
    __tablename__ = "lab_attestations"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"), index=True)
    lab_actor_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    event_id: Mapped[UUID] = mapped_column(ForeignKey("batch_events.id"))
    commitment: Mapped[str] = mapped_column(String(64), unique=True)
    policy_id: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="RECORDED_UNVERIFIED")


class ChainJob(Base):
    __tablename__ = "chain_jobs"
    __table_args__ = (UniqueConstraint("network", "tx_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"), index=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    operation: Mapped[str] = mapped_column(String(30))
    network: Mapped[str] = mapped_column(String(30))
    contract_address: Mapped[str] = mapped_column(String(64))
    intent: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="PREPARED")
    tx_id: Mapped[str | None] = mapped_column(String(64))
    receipt: Mapped[dict | None] = mapped_column(JSONB)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransformEdge(Base):
    __tablename__ = "transform_edges"
    job_id: Mapped[UUID] = mapped_column(ForeignKey("chain_jobs.id"), primary_key=True)
    input_batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"), primary_key=True)
    output_batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"), primary_key=True)


class AdministrationEvent(Base):
    __tablename__ = "administration_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    target_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    action: Mapped[str] = mapped_column(String(40))
    command: Mapped[dict] = mapped_column(JSONB)
    signature: Mapped[str | None] = mapped_column(String(88))
    signing_public_key: Mapped[bytes] = mapped_column(LargeBinary)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
