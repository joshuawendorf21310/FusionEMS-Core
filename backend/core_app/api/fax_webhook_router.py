from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.documents.s3_storage import put_bytes
from core_app.services import sqs_publisher
from core_app.telnyx.client import TelnyxApiError, download_media
from core_app.telnyx.signature import verify_telnyx_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telnyx Fax"])


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _s3_fax_key(tenant_id: str, fax_id: str) -> str:
    now = datetime.now(UTC)
    return f"tenant/{tenant_id}/fax/{now.year}/{now.month:02d}/{now.day:02d}/{fax_id}/original.pdf"


def _resolve_tenant_by_did(db: Session, to_number: str) -> str | None:
    row = db.execute(
        text(
            "SELECT tenant_id FROM tenant_phone_numbers "
            "WHERE phone_e164 = :phone AND purpose = 'billing_fax' LIMIT 1"
        ),
        {"phone": to_number},
    ).fetchone()
    return str(row.tenant_id) if row else None


def _insert_event(db: Session, event_id: str, event_type: str, tenant_id: str | None, raw: dict) -> bool:
    result = db.execute(
        text(
            "INSERT INTO telnyx_events (event_id, event_type, tenant_id, received_at, raw_json) "
            "VALUES (:eid, :etype, :tid, :now, :raw::jsonb) "
            "ON CONFLICT (event_id) DO NOTHING"
        ),
        {
            "eid": event_id,
            "etype": event_type,
            "tid": tenant_id,
            "now": _utcnow(),
            "raw": json.dumps(raw, default=str),
        },
    )
    db.commit()
    return (result.rowcount or 0) > 0


def _route_fax_to_case(db: Session, tenant_id: str, fax_id: str, from_phone: str) -> str | None:
    """
    Attempt to route the fax to an open billing case.
    Strategy: look for most recent open billing case for the tenant with no fax_id yet.
    Returns case_id or None (UNROUTED).
    """
    row = db.execute(
        text(
            "SELECT id FROM billing_cases "
            "WHERE tenant_id = :tid AND status = 'open' "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": tenant_id},
    ).fetchone()
    return str(row.id) if row else None


def _insert_fax_document(
    db: Session,
    *,
    fax_id: str,
    tenant_id: str | None,
    from_phone: str,
    to_phone: str,
    s3_key: str | None,
    sha256: str | None,
    case_id: str | None,
    status: str,
) -> None:
    db.execute(
        text(
            "INSERT INTO fax_documents "
            "(fax_id, tenant_id, from_phone, to_phone, s3_key_original, sha256_original, "
            "doc_type, case_id, status, created_at) "
            "VALUES (:fid, :tid, :from_, :to_, :s3, :sha256, NULL, :case_id, :status, :now) "
            "ON CONFLICT (fax_id) DO UPDATE SET "
            "s3_key_original = EXCLUDED.s3_key_original, "
            "sha256_original = EXCLUDED.sha256_original, "
            "status = EXCLUDED.status"
        ),
        {
            "fid": fax_id,
            "tid": tenant_id,
            "from_": from_phone,
            "to_": to_phone,
            "s3": s3_key,
            "sha256": sha256,
            "case_id": case_id,
            "status": status,
            "now": _utcnow(),
        },
    )
    db.commit()


@router.post("/webhooks/telnyx/fax")
async def telnyx_fax_webhook(
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    raw_body = await request.body()
    settings = get_settings()

    if not verify_telnyx_webhook(
        raw_body=raw_body,
        signature_ed25519=request.headers.get("telnyx-signature-ed25519"),
        timestamp=request.headers.get("telnyx-timestamp"),
        public_key_base64=settings.telnyx_public_key,
        tolerance_seconds=settings.telnyx_webhook_tolerance_seconds,
    ):
        logger.warning("telnyx_fax_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="invalid_telnyx_signature")

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    data = payload.get("data", {})
    event_id: str = data.get("id") or str(uuid.uuid4())
    event_type: str = data.get("event_type", "")
    ep = data.get("payload", {})

    to_number: str = ep.get("to", "")
    from_number: str = ep.get("from", "")
    fax_id: str = ep.get("fax_id") or ep.get("id") or event_id
    media_url: str = ep.get("media_url") or ""

    tenant_id = _resolve_tenant_by_did(db, to_number)

    inserted = _insert_event(db, event_id, event_type, tenant_id, payload)
    if not inserted:
        logger.info("telnyx_fax_duplicate event_id=%s", event_id)
        return {"status": "duplicate"}

    logger.info(
        "telnyx_fax event_type=%s fax_id=%s from=%s to=%s tenant_id=%s",
        event_type, fax_id, from_number, to_number, tenant_id,
    )

    if event_type != "fax.received":
        db.execute(
            text("UPDATE telnyx_events SET processed_at = :now WHERE event_id = :eid"),
            {"now": _utcnow(), "eid": event_id},
        )
        db.commit()
        return {"status": "ok", "detail": "non_received_event_acked"}

    s3_key: str | None = None
    sha256_hex: str | None = None
    store_status = "pending_fetch"
    case_id: str | None = None

    api_key = settings.telnyx_api_key
    bucket = settings.s3_bucket_docs

    if api_key and bucket and media_url:
        try:
            pdf_bytes = download_media(api_key=api_key, media_url=media_url)
            sha256_hex = hashlib.sha256(pdf_bytes).hexdigest()
            s3_key = _s3_fax_key(tenant_id or "unrouted", fax_id)
            put_bytes(bucket=bucket, key=s3_key, content=pdf_bytes, content_type="application/pdf")
            store_status = "stored"
            logger.info("telnyx_fax_stored fax_id=%s s3_key=%s sha256=%s", fax_id, s3_key, sha256_hex)
        except TelnyxApiError as exc:
            logger.error("telnyx_fax_download_failed fax_id=%s error=%s", fax_id, exc)
            store_status = "download_failed"
        except Exception as exc:
            logger.error("telnyx_fax_s3_failed fax_id=%s error=%s", fax_id, exc)
            store_status = "s3_failed"
    else:
        missing = []
        if not api_key:
            missing.append("TELNYX_API_KEY")
        if not bucket:
            missing.append("S3_BUCKET_DOCS")
        if not media_url:
            missing.append("media_url_in_payload")
        logger.warning("telnyx_fax_skipping_download fax_id=%s missing=%s", fax_id, missing)

    if tenant_id and store_status == "stored":
        case_id = _route_fax_to_case(db, tenant_id, fax_id, from_number)
        if not case_id:
            logger.info("telnyx_fax_unrouted fax_id=%s tenant_id=%s", fax_id, tenant_id)

    _insert_fax_document(
        db,
        fax_id=fax_id,
        tenant_id=tenant_id,
        from_phone=from_number,
        to_phone=to_number,
        s3_key=s3_key,
        sha256=sha256_hex,
        case_id=case_id,
        status=store_status if tenant_id else "unrouted_tenant",
    )

    if store_status == "stored" and s3_key:
        queue_url = settings.fax_classify_queue_url
        if queue_url:
            job = {
                "job_type": "fax_classify_extract",
                "fax_id": fax_id,
                "tenant_id": tenant_id,
                "s3_key": s3_key,
                "sha256": sha256_hex,
                "case_id": case_id,
            }
            sqs_publisher.enqueue(
                queue_url,
                job,
                deduplication_id=fax_id,
            )
            logger.info("telnyx_fax_enqueued_classify fax_id=%s", fax_id)

    db.execute(
        text("UPDATE telnyx_events SET processed_at = :now WHERE event_id = :eid"),
        {"now": _utcnow(), "eid": event_id},
    )
    db.commit()

    return {"status": "ok", "fax_id": fax_id, "store_status": store_status}
