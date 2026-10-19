from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Actor(Base):
    __tablename__ = "actors"
    __table_args__ = (
        CheckConstraint("role IN ('admin','grower','factory','lab','blender','buyer','auditor')"),
        CheckConstraint("octet_length(signing_public_key) = 32"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    # Scoped to the single configured, verified OIDC issuer.
    subject: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    signing_public_key: Mapped[bytes] = mapped_column(LargeBinary)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint("org_id", "external_id"),
        CheckConstraint("material_class IN ('GREEN_LEAF','MADE_TEA','BLENDED_TEA')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(100))
    public_alias: Mapped[str] = mapped_column(String(100), unique=True)
    material_class: Mapped[str] = mapped_column(String(20))
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    synthetic: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BatchEvent(Base):
    __tablename__ = "batch_events"
    __table_args__ = (
        UniqueConstraint("batch_id", "sequence"),
        Index("ix_events_batch_sequence", "batch_id", "sequence"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(40))
    # The signed command contains metadata + opaque participant-encrypted content only.
    signed_command: Mapped[dict] = mapped_column(JSONB)
    signature: Mapped[str] = mapped_column(String(88))
    signing_public_key: Mapped[bytes] = mapped_column(LargeBinary)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("actors.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
