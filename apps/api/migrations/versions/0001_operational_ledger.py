"""Initial operational ledger; immutable events enforced inside PostgreSQL."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "actors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False, unique=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("signing_public_key", sa.LargeBinary(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "role IN ('admin','grower','factory','lab','blender','buyer','auditor')"
        ),
        sa.CheckConstraint("octet_length(signing_public_key) = 32"),
    )
    op.create_index("ix_actors_org_id", "actors", ["org_id"])
    op.create_table(
        "batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("public_alias", sa.String(100), nullable=False, unique=True),
        sa.Column("material_class", sa.String(20), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("org_id", "external_id"),
        sa.CheckConstraint("material_class IN ('GREEN_LEAF','MADE_TEA','BLENDED_TEA')"),
    )
    op.create_index("ix_batches_org_id", "batches", ["org_id"])
    op.create_table(
        "batch_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("actors.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("signed_command", postgresql.JSONB(), nullable=False),
        sa.Column("signature", sa.String(88), nullable=False),
        sa.Column("signing_public_key", sa.LargeBinary(), nullable=False),
        sa.Column("previous_event_hash", sa.String(64), nullable=True),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("batch_id", "sequence"),
    )
    op.create_index("ix_events_batch_sequence", "batch_events", ["batch_id", "sequence"])
    op.create_table(
        "idempotency_records",
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("actors.id"), primary_key=True),
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
    )
    op.execute("""
        CREATE FUNCTION reject_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'batch_events is append-only'; END;
        $$;
        CREATE TRIGGER immutable_batch_events BEFORE UPDATE OR DELETE ON batch_events
        FOR EACH ROW EXECUTE FUNCTION reject_event_mutation();
        CREATE TRIGGER no_truncate_batch_events BEFORE TRUNCATE ON batch_events
        FOR EACH STATEMENT EXECUTE FUNCTION reject_event_mutation();
    """)


def downgrade():
    raise RuntimeError("Destructive downgrade disabled; restore a reviewed backup instead")
