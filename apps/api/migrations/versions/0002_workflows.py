"""Signed custody, scoped evidence access and pending chain jobs."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE custody_transfers (
	id UUID NOT NULL, 
	batch_id UUID NOT NULL, 
	sender_id UUID NOT NULL, 
	receiver_id UUID NOT NULL, 
	offer_event_id UUID NOT NULL, 
	response_event_id UUID, 
	status VARCHAR(20) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(batch_id) REFERENCES batches (id), 
	FOREIGN KEY(sender_id) REFERENCES actors (id), 
	FOREIGN KEY(receiver_id) REFERENCES actors (id), 
	FOREIGN KEY(offer_event_id) REFERENCES batch_events (id), 
	FOREIGN KEY(response_event_id) REFERENCES batch_events (id)
)""")
    op.execute("""CREATE INDEX ix_custody_transfers_batch_id ON custody_transfers (batch_id)""")
    op.execute("""CREATE TABLE permission_grants (
	id UUID NOT NULL, 
	batch_id UUID NOT NULL, 
	granted_by UUID NOT NULL, 
	granted_to UUID NOT NULL, 
	scope VARCHAR(30) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	key_envelope JSONB NOT NULL, 
	event_id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(batch_id) REFERENCES batches (id), 
	FOREIGN KEY(granted_by) REFERENCES actors (id), 
	FOREIGN KEY(granted_to) REFERENCES actors (id), 
	FOREIGN KEY(event_id) REFERENCES batch_events (id)
)""")
    op.execute("""CREATE INDEX ix_permission_grants_batch_id ON permission_grants (batch_id)""")
    op.execute("""CREATE INDEX ix_permission_grants_granted_to ON permission_grants (granted_to)""")
    op.execute("""CREATE TABLE access_logs (
	id UUID NOT NULL, 
	actor_id UUID NOT NULL, 
	grant_id UUID NOT NULL, 
	batch_id UUID NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES actors (id), 
	FOREIGN KEY(grant_id) REFERENCES permission_grants (id), 
	FOREIGN KEY(batch_id) REFERENCES batches (id)
)""")
    op.execute("""CREATE TABLE lab_attestations (
	id UUID NOT NULL, 
	batch_id UUID NOT NULL, 
	lab_actor_id UUID NOT NULL, 
	event_id UUID NOT NULL, 
	commitment VARCHAR(64) NOT NULL, 
	policy_id VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(batch_id) REFERENCES batches (id), 
	FOREIGN KEY(lab_actor_id) REFERENCES actors (id), 
	FOREIGN KEY(event_id) REFERENCES batch_events (id), 
	UNIQUE (commitment)
)""")
    op.execute("""CREATE INDEX ix_lab_attestations_batch_id ON lab_attestations (batch_id)""")
    op.execute("""CREATE TABLE chain_jobs (
	id UUID NOT NULL, 
	batch_id UUID NOT NULL, 
	actor_id UUID NOT NULL, 
	operation VARCHAR(30) NOT NULL, 
	network VARCHAR(30) NOT NULL, 
	contract_address VARCHAR(64) NOT NULL, 
	intent JSONB NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	tx_id VARCHAR(64), 
	receipt JSONB, 
	last_checked_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (network, tx_id), 
	FOREIGN KEY(batch_id) REFERENCES batches (id), 
	FOREIGN KEY(actor_id) REFERENCES actors (id)
)""")
    op.execute("""CREATE INDEX ix_chain_jobs_batch_id ON chain_jobs (batch_id)""")
    op.execute("""CREATE TABLE transform_edges (
	job_id UUID NOT NULL, 
	input_batch_id UUID NOT NULL, 
	output_batch_id UUID NOT NULL, 
	PRIMARY KEY (job_id, input_batch_id, output_batch_id), 
	FOREIGN KEY(job_id) REFERENCES chain_jobs (id), 
	FOREIGN KEY(input_batch_id) REFERENCES batches (id), 
	FOREIGN KEY(output_batch_id) REFERENCES batches (id)
)""")
    op.execute("""
      CREATE TRIGGER immutable_access_logs BEFORE UPDATE OR DELETE ON access_logs
        FOR EACH ROW EXECUTE FUNCTION reject_event_mutation();
      CREATE TRIGGER no_truncate_access_logs BEFORE TRUNCATE ON access_logs
        FOR EACH STATEMENT EXECUTE FUNCTION reject_event_mutation();
      CREATE UNIQUE INDEX one_pending_custody_per_batch ON custody_transfers(batch_id)
        WHERE status = 'OFFERED';
    """)


def downgrade():
    raise RuntimeError("Destructive downgrade disabled; restore a reviewed backup instead")
