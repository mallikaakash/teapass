import base64
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from teapass.administration import SignedActorCommand, manage_actor
from teapass.config import Settings
from teapass.db import make_database
from teapass.epcis import Document, export_document
from teapass.ledger import append_event, event_view, head_event, owned_batch, reserve_operation
from teapass.middleware import RequestBoundary
from teapass.models import Actor, Batch, BatchEvent, Organization
from teapass.public_proofs import PublicProof, read_proof
from teapass.schemas import ActorEnrollment, CommandResult, PublicBatch, SignedBatch, SignedEvent
from teapass.security import TokenVerifier, batch_reference, verify_command
from teapass.workflow_models import (
    AccessLog,
    AdministrationEvent,
    ChainJob,
    Custody,
    LabAttestation,
    PermissionGrant,
    TransformEdge,
)
from teapass.workflow_schemas import PrepareChain, SignedWorkflow, SubmitChain
from teapass.workflows import execute_workflow, grant_for

bearer = HTTPBearer(auto_error=False)
IdempotencyKey = Annotated[str, Header(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    engine, sessions = make_database(settings)
    verifier = TokenVerifier(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(
        title="TeaPass API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.state.sessions = sessions
    app.state.engine = engine
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestBoundary, max_bytes=settings.max_request_bytes)

    def database():
        with sessions() as db, db.begin():
            yield db

    def current_actor(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        db: Session = Depends(database, scope="function"),
    ):
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                401, "AUTHENTICATION_REQUIRED", headers={"WWW-Authenticate": "Bearer"}
            )
        subject = verifier.subject(credentials.credentials)
        actor = db.scalar(
            select(Actor)
            .join(Organization)
            .where(Actor.subject == subject, Actor.active.is_(True), Organization.active.is_(True))
            .with_for_update(of=Actor)
        )
        if actor is None:
            raise HTTPException(403, "ACTOR_NOT_ENROLLED_OR_INACTIVE")
        return actor

    def operator(actor: Actor = Depends(current_actor, scope="function")):
        if actor.role not in {"grower", "factory", "blender"}:
            raise HTTPException(403, "OPERATOR_ROLE_REQUIRED")
        return actor

    def private_reader(actor: Actor = Depends(current_actor, scope="function")):
        if actor.role not in {"admin", "grower", "factory", "blender"}:
            raise HTTPException(403, "PRIVATE_BATCH_ACCESS_DENIED")
        return actor

    def error(request, code, status, headers=None):
        return JSONResponse(
            {"error": {"code": code, "request_id": request.state.request_id}},
            status_code=status,
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return error(request, str(exc.detail), exc.status_code, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # FastAPI's default includes rejected input values; do not echo sensitive bodies.
        response = error(request, "INVALID_REQUEST", 422)
        return response

    @app.exception_handler(IntegrityError)
    async def conflict_error(request: Request, exc: IntegrityError):
        return error(request, "RESOURCE_CONFLICT", 409)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return error(request, "DATABASE_UNAVAILABLE", 503)

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready(db: Session = Depends(database, scope="function")):
        # A reachable but unmigrated database is not ready.
        if db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() != "0003":
            raise HTTPException(503, "DATABASE_SCHEMA_MISMATCH")
        return {
            "status": "ok",
            "chain": "configured"
            if settings.midnight_contract_address and settings.midnight_verifier_url
            else "unavailable",
        }

    @app.get("/v1/me")
    def me(actor: Actor = Depends(current_actor, scope="function")):
        return {
            "actor_id": str(actor.id),
            "org_id": str(actor.org_id),
            "role": actor.role,
            "deployment_id": settings.deployment_id,
        }

    @app.post("/v1/actors", status_code=201)
    def enroll(
        body: ActorEnrollment,
        idempotency_key: IdempotencyKey,
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        if actor.role != "admin":
            raise HTTPException(403, "ADMIN_ROLE_REQUIRED")
        record, prior = reserve_operation(
            db, actor.id, idempotency_key, "/v1/actors", body.model_dump(mode="json")
        )
        if prior:
            return prior
        created = Actor(
            org_id=actor.org_id,
            subject=body.subject,
            role=body.role,
            signing_public_key=base64.b64decode(body.signing_public_key, validate=True),
        )
        db.add(created)
        db.flush()
        db.add(
            AdministrationEvent(
                actor_id=actor.id,
                org_id=actor.org_id,
                target_id=created.id,
                action="ENROLL_ACTOR",
                command=body.model_dump(mode="json"),
                signature=None,
                signing_public_key=actor.signing_public_key,
            )
        )
        result = {"actor_id": str(created.id), "org_id": str(created.org_id), "role": created.role}
        record.response, record.status_code = result, 201
        return result

    @app.post("/v1/actors/lifecycle")
    def actor_lifecycle(
        body: SignedActorCommand,
        idempotency_key: IdempotencyKey,
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        return manage_actor(db, body, actor, settings, idempotency_key)

    @app.post("/v1/batches", response_model=CommandResult, status_code=201)
    def create_batch(
        body: SignedBatch,
        idempotency_key: IdempotencyKey,
        actor: Actor = Depends(operator, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        command = body.command
        verify_command(command, body.signature, actor, settings)
        record, prior = reserve_operation(
            db, actor.id, idempotency_key, "/v1/batches", body.model_dump(mode="json")
        )
        if prior:
            return prior
        db.add(
            Batch(
                id=command.batch_id,
                org_id=actor.org_id,
                external_id=command.external_id,
                public_alias=command.public_alias,
                material_class=command.material_class,
                published=command.published,
                synthetic=command.synthetic,
            )
        )
        db.flush()
        result = append_event(db, command, body.signature, actor, "LOT_RECORDED", None)
        record.response, record.status_code = result, 201
        return result

    @app.post("/v1/batches/{batch_id}/events", response_model=CommandResult, status_code=201)
    def add_event(
        batch_id: UUID,
        body: SignedEvent,
        idempotency_key: IdempotencyKey,
        actor: Actor = Depends(operator, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        command = body.command
        verify_command(command, body.signature, actor, settings)
        if command.batch_id != batch_id:
            raise HTTPException(422, "BATCH_BINDING_MISMATCH")
        record, prior = reserve_operation(
            db,
            actor.id,
            idempotency_key,
            f"/v1/batches/{batch_id}/events",
            body.model_dump(mode="json"),
        )
        if prior:
            return prior
        owned_batch(db, batch_id, actor, lock=True)
        previous = head_event(db, batch_id)
        if previous is None or previous.event_hash != command.previous_event_hash:
            raise HTTPException(409, "STALE_EVENT_PARENT")
        if command.event_type == "CORRECTION_RECORDED":
            target = db.scalar(
                select(BatchEvent).where(
                    BatchEvent.id == command.supersedes_event_id, BatchEvent.batch_id == batch_id
                )
            )
            if target is None:
                raise HTTPException(422, "CORRECTION_TARGET_REQUIRED")
        elif command.supersedes_event_id is not None:
            raise HTTPException(422, "UNEXPECTED_CORRECTION_TARGET")
        result = append_event(db, command, body.signature, actor, command.event_type, previous)
        record.response, record.status_code = result, 201
        return result

    @app.get("/v1/private/batches/{batch_id}/events")
    def events(
        batch_id: UUID,
        after_sequence: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=100),
        actor: Actor = Depends(private_reader, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        owned_batch(db, batch_id, actor)
        rows = db.scalars(
            select(BatchEvent)
            .where(BatchEvent.batch_id == batch_id, BatchEvent.sequence > after_sequence)
            .order_by(BatchEvent.sequence)
            .limit(limit + 1)
        ).all()
        page = rows[:limit]
        return {
            "events": [event_view(row) for row in page],
            "next_after_sequence": page[-1].sequence if len(rows) > limit else None,
        }

    @app.get("/v1/private/batches/{batch_id}/lineage")
    def lineage(
        batch_id: UUID,
        actor: Actor = Depends(private_reader, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        owned_batch(db, batch_id, actor)
        # Bounded breadth-first traversal, filtered on every node to prevent tenant leakage.
        seen, frontier, edges = {batch_id}, [batch_id], []
        for _ in range(20):
            if not frontier:
                break
            rows = db.execute(
                select(TransformEdge, ChainJob)
                .join(ChainJob, ChainJob.id == TransformEdge.job_id)
                .join(Batch, Batch.id == TransformEdge.input_batch_id)
                .where(TransformEdge.output_batch_id.in_(frontier), Batch.org_id == actor.org_id)
                .limit(201)
            ).all()
            if len(rows) > 200 or len(edges) + len(rows) > 200:
                raise HTTPException(422, "LINEAGE_LIMIT_EXCEEDED")
            frontier = []
            for edge, job in rows:
                edges.append(
                    {
                        "input_batch_id": str(edge.input_batch_id),
                        "output_batch_id": str(edge.output_batch_id),
                        "job_id": str(job.id),
                        "chain_status": job.status,
                        "semantic_verification": "NOT_VERIFIED",
                    }
                )
                if edge.input_batch_id not in seen:
                    seen.add(edge.input_batch_id)
                    frontier.append(edge.input_batch_id)
        return {"batch_id": str(batch_id), "edges": edges, "truncated": bool(frontier)}

    @app.get("/v1/public/batches/{alias}", response_model=PublicBatch)
    def public_batch(alias: str, db: Session = Depends(database, scope="function")):
        batch = db.scalar(
            select(Batch).where(Batch.public_alias == alias, Batch.published.is_(True))
        )
        if batch is None:
            raise HTTPException(404, "BATCH_NOT_FOUND")
        claims, verification_status = [], "NOT_VERIFIED"
        if settings.midnight_contract_address and settings.midnight_verifier_url:
            references = db.scalars(
                select(LabAttestation)
                .join(BatchEvent, BatchEvent.id == LabAttestation.event_id)
                .where(LabAttestation.batch_id == batch.id)
                .order_by(BatchEvent.recorded_at.desc())
                .limit(5)
            ).all()
            expected_reference = batch_reference(settings.deployment_id, batch.id)
            expected_material = {"GREEN_LEAF": "1", "MADE_TEA": "2", "BLENDED_TEA": "3"}[
                batch.material_class
            ]
            for attestation in references:
                try:
                    proof = read_proof(settings, attestation.commitment)
                except HTTPException as exc:
                    if exc.status_code == 404:
                        continue
                    claims, verification_status = [], "UNAVAILABLE"
                    break
                if (
                    proof.batchReference == expected_reference
                    and proof.materialClass == expected_material
                    and proof.policyId == attestation.policy_id
                ):
                    claims.append(proof.model_dump(mode="json"))
            if claims:
                verification_status = (
                    "VERIFIED_CLAIMS"
                    if all(c["status"] == "VALID" for c in claims)
                    else "INVALID_CLAIMS"
                )
        return PublicBatch(
            public_alias=batch.public_alias,
            material_class=batch.material_class,
            synthetic=batch.synthetic,
            verification_status=verification_status,
            claims=claims,
            checked_at=datetime.now(UTC),
            limitations=[
                "Only listed lab predicates are checked; no blanket safety or origin claim.",
                "A copied QR does not authenticate a physical package.",
                "At most five most recently recorded laboratory references are evaluated.",
            ],
        )

    @app.get("/v1/public/proofs/{claim_id}", response_model=PublicProof)
    def public_proof(claim_id: str = Path(pattern=r"^[a-f0-9]{64}$")):
        return read_proof(settings, claim_id)

    @app.post("/v1/workflows", response_model=CommandResult, status_code=201)
    def workflow(
        body: SignedWorkflow,
        idempotency_key: IdempotencyKey,
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        return execute_workflow(db, body, actor, settings, idempotency_key)

    @app.post("/v1/labs/attestations", response_model=CommandResult, status_code=201)
    def lab_attestation(
        body: SignedWorkflow,
        idempotency_key: IdempotencyKey,
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        if body.command.command_type != "ATTEST_LAB":
            raise HTTPException(422, "WRONG_COMMAND_TYPE")
        return execute_workflow(db, body, actor, settings, idempotency_key)

    @app.get("/v1/custody/{transfer_id}")
    def custody(
        transfer_id: UUID,
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        row = db.get(Custody, transfer_id)
        if row is None or actor.id not in {row.sender_id, row.receiver_id}:
            raise HTTPException(404, "CUSTODY_OFFER_NOT_FOUND")
        head = head_event(db, row.batch_id)
        return {
            "transfer_id": str(row.id),
            "batch_id": str(row.batch_id),
            "status": "EXPIRED"
            if row.status == "OFFERED" and row.expires_at <= datetime.now(UTC)
            else row.status,
            "expires_at": row.expires_at,
            "current_event_hash": head.event_hash,
            "offer": event_view(db.get(BatchEvent, row.offer_event_id)),
            "response": event_view(db.get(BatchEvent, row.response_event_id))
            if row.response_event_id
            else None,
            "inventory_ownership": "UNCHANGED_BY_CUSTODY",
        }

    @app.get("/v1/audit/grants/{grant_id}/events")
    def audit_events(
        grant_id: UUID,
        after_sequence: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=100),
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        grant = db.scalar(
            select(PermissionGrant)
            .where(
                PermissionGrant.id == grant_id,
                PermissionGrant.granted_to == actor.id,
                PermissionGrant.scope == "events",
                PermissionGrant.revoked_at.is_(None),
                PermissionGrant.expires_at > datetime.now(UTC),
            )
            .with_for_update()
        )
        if actor.role != "auditor" or grant is None:
            raise HTTPException(404, "ACTIVE_GRANT_NOT_FOUND")
        db.add(
            AccessLog(
                actor_id=actor.id, grant_id=grant.id, batch_id=grant.batch_id, action="READ_EVENTS"
            )
        )
        rows = db.scalars(
            select(BatchEvent)
            .where(BatchEvent.batch_id == grant.batch_id, BatchEvent.sequence > after_sequence)
            .order_by(BatchEvent.sequence)
            .limit(limit + 1)
        ).all()
        return {
            "events": [event_view(row) for row in rows[:limit]],
            "key_envelope": grant.key_envelope,
            "next_after_sequence": rows[limit - 1].sequence if len(rows) > limit else None,
        }

    @app.get("/v1/labs/batches/{batch_id}/head")
    def lab_head(
        batch_id: UUID,
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        if actor.role != "lab" or not grant_for(db, actor, batch_id, "lab_attest"):
            raise HTTPException(404, "ACTIVE_GRANT_NOT_FOUND")
        return {"batch_id": str(batch_id), "event_hash": head_event(db, batch_id).event_hash}

    @app.get("/v1/transactions/{job_id}")
    def transaction(
        job_id: UUID,
        actor: Actor = Depends(current_actor, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        if actor.role not in {"admin", "grower", "factory", "blender", "lab"}:
            raise HTTPException(403, "PRIVATE_BATCH_ACCESS_DENIED")
        access = ChainJob.actor_id == actor.id
        if actor.role != "lab":
            access = access | (Batch.org_id == actor.org_id)
        job = db.scalar(select(ChainJob).join(Batch).where(ChainJob.id == job_id, access))
        if job is None:
            raise HTTPException(404, "CHAIN_JOB_NOT_FOUND")
        return {
            "job_id": str(job.id),
            "status": job.status,
            "network": job.network,
            "contract_address": job.contract_address,
            "tx_id": job.tx_id,
            "receipt": job.receipt,
            "last_checked_at": job.last_checked_at,
            "semantic_verification": "NOT_VERIFIED",
        }

    @app.get("/v1/integrations/epcis/export/{batch_id}")
    def epcis_export(
        batch_id: UUID,
        actor: Actor = Depends(private_reader, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        owned_batch(db, batch_id, actor)
        rows = db.scalars(
            select(BatchEvent)
            .where(BatchEvent.batch_id == batch_id)
            .order_by(BatchEvent.sequence)
            .limit(101)
        ).all()
        if len(rows) > 100:
            raise HTTPException(422, "EXPORT_LIMIT_EXCEEDED")
        return export_document(rows)

    @app.post("/v1/integrations/epcis/import")
    def epcis_import(
        body: Document,
        idempotency_key: IdempotencyKey,
        actor: Actor = Depends(operator, scope="function"),
        db: Session = Depends(database, scope="function"),
    ):
        commands = body.signed_events()
        record, prior = reserve_operation(
            db,
            actor.id,
            idempotency_key,
            "/v1/integrations/epcis/import",
            body.model_dump(mode="json", by_alias=True),
        )
        if prior:
            return prior
        imported = []
        for signed in commands:
            c = signed.command
            verify_command(c, signed.signature, actor, settings)
            existing = db.get(BatchEvent, c.operation_id)
            if existing is not None:
                if (
                    existing.signed_command != c.model_dump(mode="json")
                    or existing.signature != signed.signature
                ):
                    raise HTTPException(409, "IMPORTED_EVENT_CONFLICT")
                imported.append({"event_id": str(existing.id), "status": "ALREADY_RECORDED"})
                continue
            key = "epcis-" + str(c.operation_id)
            if isinstance(signed, SignedBatch):
                result = create_batch(signed, key, actor, db)
            else:
                result = add_event(c.batch_id, signed, key, actor, db)
            imported.append(result)
        result = {
            "mapping_version": "teapass-epcis-1",
            "events": imported,
            "verification": "SIGNED_OPERATIONAL_RECORDS_ONLY",
        }
        record.response, record.status_code = result, 200
        return result

    def chain_endpoint(command_type, operations):
        def endpoint(
            body: SignedWorkflow,
            idempotency_key: IdempotencyKey,
            actor: Actor = Depends(current_actor, scope="function"),
            db: Session = Depends(database, scope="function"),
        ):
            if not settings.midnight_contract_address:
                raise HTTPException(503, "MIDNIGHT_NOT_CONFIGURED")
            c = body.command
            if c.command_type != command_type:
                raise HTTPException(422, "WRONG_COMMAND_TYPE")
            if isinstance(c, PrepareChain) and c.operation not in operations:
                raise HTTPException(422, "WRONG_CHAIN_OPERATION")
            if isinstance(c, SubmitChain):
                job = db.scalar(
                    select(ChainJob).where(ChainJob.id == c.job_id, ChainJob.actor_id == actor.id)
                )
                if job is None or job.operation not in operations:
                    raise HTTPException(404, "CHAIN_JOB_NOT_FOUND")
            return execute_workflow(db, body, actor, settings, idempotency_key)

        return endpoint

    for route, command_type, operations in [
        ("issuances/prepare", "PREPARE_CHAIN", {"issue"}),
        ("issuances/submit", "SUBMIT_CHAIN", {"issue"}),
        ("transforms/prepare", "PREPARE_CHAIN", {"transfer", "split", "blend", "process"}),
        ("transforms/submit", "SUBMIT_CHAIN", {"transfer", "split", "blend", "process"}),
        ("proofs/compliance", "PREPARE_CHAIN", {"proveCompliance"}),
    ]:
        app.add_api_route(
            f"/v1/{route}",
            chain_endpoint(command_type, operations),
            methods=["POST"],
            status_code=201,
            name=route.replace("/", "_"),
        )

    return app
