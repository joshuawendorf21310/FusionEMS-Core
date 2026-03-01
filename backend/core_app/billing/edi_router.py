from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.ai.service import AiService
from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.billing.edi_service import EDIService
from core_app.core.config import get_settings
from core_app.repositories.domination_repository import DominationRepository
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.sqs_publisher import enqueue

router = APIRouter(prefix="/api/v1/edi", tags=["EDI"])


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


class GenerateBatchRequest(BaseModel):
    claim_ids: list[str] = Field(..., min_length=1)
    submitter_config: dict[str, Any] = Field(default_factory=dict)


class Ingest999Request(BaseModel):
    x12_content: str
    batch_id: str


class Ingest277Request(BaseModel):
    x12_content: str


class Ingest835Request(BaseModel):
    x12_content: str


@router.post("/batches/generate")
async def generate_batch(
    body: GenerateBatchRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    publisher = get_event_publisher()
    svc = EDIService(db, publisher, current.tenant_id)
    result = await svc.generate_837_batch(body.claim_ids, body.submitter_config)
    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.edi.batch.generated",
        tenant_id=current.tenant_id,
        entity_id=result.get("batch_id"),
        entity_type="edi_batch",
        event_type="EDI_BATCH_GENERATED",
        payload=result,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


@router.get("/batches")
async def list_batches(
    limit: int = 50,
    offset: int = 0,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    repo = DominationRepository(db, table="edi_artifacts")
    all_artifacts = repo.list(tenant_id=current.tenant_id, limit=limit, offset=offset)
    batches = [
        a for a in all_artifacts if (a.get("data") or {}).get("entity_type") == "submission_batch"
    ]
    return {"batches": batches, "total": len(batches)}


@router.get("/batches/{batch_id}")
async def get_batch(
    batch_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    repo = DominationRepository(db, table="edi_artifacts")
    batch = repo.get(tenant_id=current.tenant_id, record_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="batch_not_found")

    all_artifacts = repo.list(tenant_id=current.tenant_id, limit=1000)
    edi_files = [
        a
        for a in all_artifacts
        if (a.get("data") or {}).get("entity_type") == "edi_file"
        and (a.get("data") or {}).get("batch_id") == str(batch_id)
    ]
    return {"batch": batch, "edi_files": edi_files}


@router.get("/batches/{batch_id}/download")
async def download_batch(
    batch_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    repo = DominationRepository(db, table="edi_artifacts")
    batch = repo.get(tenant_id=current.tenant_id, record_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="batch_not_found")

    bdata = batch.get("data") or {}
    content_b64 = bdata.get("content_b64", "")
    if not content_b64:
        raise HTTPException(status_code=404, detail="no_content_available")

    try:
        x12_bytes = base64.b64decode(content_b64.encode("ascii"))
    except Exception:
        raise HTTPException(status_code=500, detail="content_decode_error")

    filename = f"837P_batch_{batch_id}.x12"
    return Response(
        content=x12_bytes,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/batches/{batch_id}/submit-sftp")
async def submit_batch_sftp(
    batch_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    DominationService(db, get_event_publisher())
    repo = DominationRepository(db, table="edi_artifacts")
    batch = repo.get(tenant_id=current.tenant_id, record_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="batch_not_found")

    settings = get_settings()
    sftp_queue_url = getattr(settings, "officeally_sftp_queue_url", "") or ""
    if not sftp_queue_url:
        raise HTTPException(status_code=500, detail="officeally_sftp_queue_url_not_configured")

    sftp_path = f"/claims/837P/837P_batch_{batch_id}.x12"
    try:
        enqueue(
            sftp_queue_url,
            {
                "job_type": "officeally.sftp.send",
                "batch_id": str(batch_id),
                "sftp_path": sftp_path,
                "tenant_id": str(current.tenant_id),
                "queued_at": _utcnow(),
            },
            deduplication_id=str(batch_id),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"sftp_queue_error: {exc}")

    batch_uuid = uuid.UUID(str(batch["id"]))
    repo.update(
        tenant_id=current.tenant_id,
        record_id=batch_uuid,
        expected_version=batch["version"],
        patch={"status": "sftp_queued", "sftp_queued_at": _utcnow(), "sftp_path": sftp_path},
    )
    db.commit()

    return {"batch_id": str(batch_id), "sftp_path": sftp_path, "status": "sftp_queued"}


@router.post("/ingest/999")
async def ingest_999(
    body: Ingest999Request,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    publisher = get_event_publisher()
    svc = EDIService(db, publisher, current.tenant_id)
    result = svc.parse_999(body.x12_content, body.batch_id)
    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.edi.999.received",
        tenant_id=current.tenant_id,
        entity_id=body.batch_id,
        entity_type="edi_batch",
        event_type="EDI_999_RECEIVED",
        payload=result,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


@router.post("/ingest/277")
async def ingest_277(
    body: Ingest277Request,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    publisher = get_event_publisher()
    svc = EDIService(db, publisher, current.tenant_id)
    result = svc.parse_277(body.x12_content)
    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.edi.277.received",
        tenant_id=current.tenant_id,
        entity_id=uuid.uuid4(),
        entity_type="claim_status",
        event_type="EDI_277_RECEIVED",
        payload=result,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


@router.post("/ingest/835")
async def ingest_835(
    body: Ingest835Request,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    publisher = get_event_publisher()
    svc = EDIService(db, publisher, current.tenant_id)
    result = await svc.parse_835(body.x12_content)
    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.edi.835.received",
        tenant_id=current.tenant_id,
        entity_id=uuid.uuid4(),
        entity_type="era",
        event_type="EDI_835_RECEIVED",
        payload={
            "denial_count": len(result.get("denials", [])),
            "payment_amount": result.get("payment_amount"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


@router.get("/claims/{claim_id}/status-history")
async def claim_status_history(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing", "ems"):
        raise HTTPException(status_code=403, detail="Forbidden")
    from sqlalchemy import text

    try:
        rows = (
            db.execute(
                text(
                    "SELECT status_code, status_description, source, effective_date, created_at "
                    "FROM claim_status_history "
                    "WHERE claim_id = :cid AND tenant_id = :tid "
                    "ORDER BY created_at DESC LIMIT 100"
                ),
                {"cid": str(claim_id), "tid": str(current.tenant_id)},
            )
            .mappings()
            .all()
        )
        history = [dict(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"status_history_query_error: {exc}")

    return {"claim_id": str(claim_id), "history": history, "total": len(history)}


@router.post("/claims/{claim_id}/explain")
async def explain_claim_status(
    claim_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    publisher = get_event_publisher()
    svc = EDIService(db, publisher, current.tenant_id)

    try:
        ai = AiService()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"ai_not_configured: {exc}")

    result = await svc.get_claim_explain(str(claim_id), ai)
    return result


_VALID_TRANSACTION_TYPES = {"999", "277", "835"}


@router.post("/ingest/{transaction_type}")
async def ingest_generic(
    transaction_type: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if transaction_type not in _VALID_TRANSACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported_transaction_type: must be one of {sorted(_VALID_TRANSACTION_TYPES)}",
        )
    try:
        body_json = await request.json()
    except Exception:
        body_json = {}

    publisher = get_event_publisher()
    svc = EDIService(db, publisher, current.tenant_id)

    if transaction_type == "999":
        x12 = body_json.get("x12_content", "")
        batch_id = body_json.get("batch_id", str(uuid.uuid4()))
        result = svc.parse_999(x12, batch_id)
        publisher.publish_sync(
            topic=f"tenant.{current.tenant_id}.edi.999.received",
            tenant_id=current.tenant_id,
            entity_id=batch_id,
            entity_type="edi_batch",
            event_type="EDI_999_RECEIVED",
            payload=result,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    elif transaction_type == "277":
        x12 = body_json.get("x12_content", "")
        result = svc.parse_277(x12)
        publisher.publish_sync(
            topic=f"tenant.{current.tenant_id}.edi.277.received",
            tenant_id=current.tenant_id,
            entity_id=uuid.uuid4(),
            entity_type="claim_status",
            event_type="EDI_277_RECEIVED",
            payload=result,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    else:
        x12 = body_json.get("x12_content", "")
        result = await svc.parse_835(x12)
        publisher.publish_sync(
            topic=f"tenant.{current.tenant_id}.edi.835.received",
            tenant_id=current.tenant_id,
            entity_id=uuid.uuid4(),
            entity_type="era",
            event_type="EDI_835_RECEIVED",
            payload={
                "denial_count": len(result.get("denials", [])),
                "payment_amount": result.get("payment_amount"),
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )

    return result
