-- Apply as the migration/database owner after migrations. No credentials are embedded.
-- Grant teapass_runtime to a separately provisioned LOGIN role and use that role in the API.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'teapass_runtime') THEN
    CREATE ROLE teapass_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
  END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO teapass_runtime;
GRANT SELECT ON alembic_version, organizations, actors, batches, batch_events,
  idempotency_records, custody_transfers, permission_grants, access_logs,
  lab_attestations, chain_jobs, transform_edges, administration_events TO teapass_runtime;
GRANT INSERT ON actors, batches, batch_events, idempotency_records, custody_transfers,
  permission_grants, access_logs, lab_attestations, chain_jobs, transform_edges, administration_events TO teapass_runtime;
GRANT UPDATE ON idempotency_records, custody_transfers, permission_grants, chain_jobs TO teapass_runtime;
-- No DELETE, TRUNCATE, schema ownership, trigger management or credential UPDATE rights.
-- This role limits DB capabilities; per-tenant authorization is enforced by application queries.

GRANT UPDATE (signing_public_key, active) ON actors TO teapass_runtime;
