from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi import Depends

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.integrations.lob_service import verify_lob_webhook_signature
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.sqs_publisher import enqueue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks - Lob"])


# Canonical Lob event types we handle
LOB_HANDLED_EVENTS = frozenset({
    "address.created",
    "address.deleted",
    "letter.created",
    "letter.deleted",
    "letter.failed",
    "letter.rejected",
    "letter.rendered_pdf",
    "letter.rendered_thumbnails",
    "letter.viewed",
    "letter.billed",
})


@router.post("/webhooks/lob", include_in_schema=True)
async def lob_webhook(
    request: Request,
    db: Session = Depends(db_session_dependency),
    lob_signature: str = Header(default="", alias="Lob-Signature"),
    lob_signature_timestamp: str = Header(default="", alias="Lob-Signature-Timestamp"),
):
    """
    Lob webhook receiver.

    1. Read raw body (must happen before any .json() call).
    2. Verify HMAC-SHA256 signature with timestamp tolerance.
    3. Idempotency check (unique by lob_event_id).
    4. Persist raw receipt.
    5. Enqueue to SQS for async processing.
    6. Return 200 immediately.
    """
    raw_body = await request.body()
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

    # ── 1. Signature verification ─────────────────────────────────────────────
    settings = get_settings()
    webhook_secret = getattr(settings, "lob_webhook_secret", "")

    if not webhook_secret or webhook_secret.startswith("REPLACE"):
        logger.error("lob_webhook_secret_not_configured correlation_id=%s", correlation_id)
        raise HTTPException(status_code=500, detail="webhook_secret_not_configured")

    if not verify_lob_webhook_signature(
        raw_body=raw_body,
        signature_header=lob_signature,
        timestamp_header=lob_signature_timestamp,
        webhook_secret=webhook_secret,
    ):
        logger.warning(
            "lob_sig_invalid correlation_id=%s sig=%.12s ts=%s",
            correlation_id, lob_signature, lob_signature_timestamp,
        )
        raise HTTPException(status_code=400, detail="invalid_lob_signature")

    # ── 2. Parse body ─────────────────────────────────────────────────────────
    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    event_id: str = payload.get("id") or str(uuid.uuid4())
    event_type: str = (
        payload.get("event_type", {}).get("id")
        or payload.get("event_type")
        or "unknown"
    )
    payload_sha256 = hashlib.sha256(raw_body).hexdigest()

    logger.info(
        "lob_webhook_received event_id=%s event_type=%s correlation_id=%s sha256=%.16s",
        event_id, event_type, correlation_id, payload_sha256,
    )

    # ── 3. Idempotency (DB check) ─────────────────────────────────────────────
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    existing = svc.repo("lob_webhook_receipts").list_raw_by_field("event_id", event_id, limit=2)
    if existing:
        logger.info("lob_webhook_duplicate event_id=%s", event_id)
        return {"status": "duplicate", "event_id": event_id}

    # ── 4. Persist raw receipt ────────────────────────────────────────────────
    system_tenant_id = uuid.UUID(settings.system_tenant_id)
    await svc.create(
        table="lob_webhook_receipts",
        tenant_id=system_tenant_id,
        actor_user_id=None,
        data={
            "event_id": event_id,
            "event_type": event_type,
            "payload_sha256": payload_sha256,
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    # ── 5. Enqueue to SQS ─────────────────────────────────────────────────────
    queue_url = settings.lob_events_queue_url
    if not queue_url:
        logger.error(
            "lob_events_queue_url_not_configured — cannot enqueue event_id=%s",
            event_id,
        )
        raise HTTPException(status_code=500, detail="lob_events_queue_not_configured")
    enqueue(
        queue_url,
        {
            "source": "lob_webhook",
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "payload_sha256": payload_sha256,
            "correlation_id": correlation_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
        deduplication_id=event_id,
    )

    return {"status": "ok", "event_id": event_id, "event_type": event_type}
