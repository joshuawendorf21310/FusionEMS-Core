from __future__ import annotations

import hashlib
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.documents.s3_storage import default_docs_bucket, put_bytes
from core_app.fax.telnyx_service import TelnyxConfig, TelnyxNotConfigured, download_media
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1", tags=["Fax"])


@router.post("/fax/send")
async def send_fax(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    # Outbound fax job record (actual Telnyx send happens in worker once configured)
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    get_event_publisher().publish(
        topic=f"tenant.{current.tenant_id}.fax.job.created",
        tenant_id=current.tenant_id,
        entity_type="fax_job",
        entity_id=row["id"],
        event_type="FAX_JOB_CREATED",
        payload={"fax_job_id": row["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.post("/webhooks/telnyx/fax/inbound", include_in_schema=True)
async def inbound_fax(
    payload: dict[str, Any], request: Request, db: Session = Depends(db_session_dependency)
):
    """
    Telnyx inbound fax webhook (billing/docs). Stores an idempotent receipt, creates a fax_event,
    and creates a document record. If Telnyx API key is configured, downloads media and uploads to S3.
    """
    tenant_id_raw = payload.get("tenant_id")
    if not tenant_id_raw:
        raise HTTPException(status_code=400, detail="tenant_id_required")

    try:
        tenant_id = uuid.UUID(str(tenant_id_raw))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_tenant_id")

    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id_required")

    settings = get_settings()
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    event_id = payload.get("data", {}).get("id") or payload.get("id") or str(uuid.uuid4())
    raw = (str(payload)).encode("utf-8")
    payload_hash = hashlib.sha256(raw).hexdigest()

    # Idempotency receipt
    existing = svc.repo("telnyx_webhook_receipts").list(tenant_id, limit=2000)
    if any(r["data"].get("event_id") == event_id for r in existing):
        return {"status": "duplicate", "event_id": event_id}

    await svc.create(
        table="telnyx_webhook_receipts",
        tenant_id=tenant_id,
        actor_user_id=None,
        data={"event_id": event_id, "payload_hash": payload_hash, "payload": payload},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    fax_event = await svc.create(
        table="fax_events",
        tenant_id=tenant_id,
        actor_user_id=None,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    # Try to fetch fax media if available
    media_url = payload.get("data", {}).get("payload", {}).get("media_url") or payload.get(
        "media_url"
    )
    bucket = default_docs_bucket()
    doc_key = None
    if bucket and media_url and settings.telnyx_api_key:
        try:
            tel_cfg = TelnyxConfig(
                api_key=settings.telnyx_api_key,
                messaging_profile_id=settings.telnyx_messaging_profile_id or None,
            )
            content = download_media(cfg=tel_cfg, media_url=media_url)
            doc_key = f"tenants/{tenant_id}/fax/inbound/{event_id}.pdf"
            put_bytes(bucket=bucket, key=doc_key, content=content, content_type="application/pdf")
        except TelnyxNotConfigured:
            doc_key = None

    doc_row = await svc.create(
        table="documents",
        tenant_id=tenant_id,
        actor_user_id=None,
        data={
            "source": "telnyx_fax",
            "fax_event_id": fax_event["id"],
            "bucket": bucket,
            "s3_key": doc_key,
            "media_url": media_url,
            "doc_type": "fax_inbound",
            "status": "stored" if doc_key else "pending_fetch",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    publisher.publish(
        topic=f"tenant.{tenant_id}.documents.fax.received",
        tenant_id=tenant_id,
        entity_type="document",
        entity_id=doc_row["id"],
        event_type="FAX_DOCUMENT_RECEIVED",
        payload={"document_id": doc_row["id"], "fax_event_id": fax_event["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    return {"status": "ok", "fax_event_id": fax_event["id"], "document_id": doc_row["id"]}


@router.get("/fax/inbox")
async def fax_inbox(
    request: Request,
    status: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rows = svc.repo("fax_jobs").list(tenant_id=current.tenant_id, limit=limit, offset=0)
    if status and status != "all":
        rows = [r for r in rows if (r.get("data") or {}).get("status") == status]
    return rows


@router.post("/fax/{fax_id}/match/trigger")
async def trigger_fax_match(
    fax_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "fax_job_id": str(fax_id),
            "event_type": "match_triggered",
            "triggered_by": str(current.user_id),
            "payload": payload,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    get_event_publisher().publish(
        topic=f"tenant.{current.tenant_id}.fax.match.trigger",
        tenant_id=current.tenant_id,
        entity_type="fax_job",
        entity_id=str(fax_id),
        event_type="FAX_MATCH_TRIGGERED",
        payload={"fax_job_id": str(fax_id), "fax_event_id": row["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "triggered", "fax_event_id": row["id"]}


@router.post("/fax/{fax_id}/match/detach")
async def detach_fax_match(
    fax_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "fax_job_id": str(fax_id),
            "event_type": "match_detached",
            "detached_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "detached", "fax_event_id": row["id"]}


@router.post("/claims/{claim_id}/documents/attach-fax")
async def attach_fax_to_claim(
    claim_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    fax_job_id = payload.get("fax_job_id")
    document_id = payload.get("document_id")

    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "claim_id": str(claim_id),
            "fax_job_id": str(fax_job_id) if fax_job_id else None,
            "document_id": str(document_id) if document_id else None,
            "event_type": "attached_to_claim",
            "attached_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    get_event_publisher().publish(
        topic=f"tenant.{current.tenant_id}.claims.fax.attached",
        tenant_id=current.tenant_id,
        entity_type="claim",
        entity_id=str(claim_id),
        event_type="FAX_ATTACHED_TO_CLAIM",
        payload={"claim_id": str(claim_id), "fax_job_id": str(fax_job_id)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "attached", "fax_event_id": row["id"]}
