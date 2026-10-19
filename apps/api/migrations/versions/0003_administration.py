"""Immutable enrollment and actor key/status administration audit."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "administration_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("actors.id"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("target_id", sa.Uuid(), sa.ForeignKey("actors.id"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("command", JSONB(), nullable=False),
        sa.Column("signature", sa.String(88)),
        sa.Column("signing_public_key", sa.LargeBinary(), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_administration_events_org_id", "administration_events", ["org_id"])
    op.execute("""
      CREATE TRIGGER immutable_administration BEFORE UPDATE OR DELETE ON administration_events
        FOR EACH ROW EXECUTE FUNCTION reject_event_mutation();
      CREATE TRIGGER no_truncate_administration BEFORE TRUNCATE ON administration_events
        FOR EACH STATEMENT EXECUTE FUNCTION reject_event_mutation();
    """)


def downgrade():
    raise RuntimeError("Destructive downgrade disabled; restore a reviewed backup instead")
