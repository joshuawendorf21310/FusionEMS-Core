from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.telnyx.client import TelnyxApiError, send_sms
from core_app.telnyx.signature import verify_telnyx_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telnyx SMS"])

STOP_KEYWORDS  = {"STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}
HELP_KEYWORDS  = {"HELP", "INFO"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _resolve_tenant_by_did(db: Session, to_number: str) -> str | None:
    row = db.execute(
        text(
            "SELECT tenant_id FROM tenant_phone_numbers "
            "WHERE phone_e164 = :phone AND purpose = 'billing_sms' LIMIT 1"
        ),
        {"phone": to_number},
    ).fetchone()
    return str(row.tenant_id) if row else None


def _get_tenant_info(db: Session, tenant_id: str) -> dict[str, Any]:
    row = db.execute(
        text("SELECT name, billing_contact_phone FROM tenants WHERE id = :tid LIMIT 1"),
        {"tid": tenant_id},
    ).fetchone()
    if row:
        return {"name": row.name or "EMS Agency", "billing_phone": row.billing_contact_phone or ""}
    return {"name": "EMS Agency", "billing_phone": ""}


def _upsert_opt_out(db: Session, tenant_id: str, phone_e164: str, source: str) -> None:
    db.execute(
        text(
            "INSERT INTO telnyx_opt_outs (tenant_id, phone_e164, opted_out_at, source) "
            "VALUES (:tid, :phone, :now, :src) "
            "ON CONFLICT (tenant_id, phone_e164) DO UPDATE SET opted_out_at = :now, source = :src"
        ),
        {"tid": tenant_id, "phone": phone_e164, "now": _utcnow(), "src": source},
    )
    db.commit()


def _is_opted_out(db: Session, tenant_id: str, phone_e164: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM telnyx_opt_outs WHERE tenant_id = :tid AND phone_e164 = :phone LIMIT 1"
        ),
        {"tid": tenant_id, "phone": phone_e164},
    ).fetchone()
    return row is not None


def _log_sms(
    db: Session,
    message_id: str,
    tenant_id: str | None,
    direction: str,
    from_phone: str,
    to_phone: str,
    body: str,
    status: str,
) -> None:
    db.execute(
        text(
            "INSERT INTO telnyx_sms_messages "
            "(message_id, tenant_id, direction, from_phone, to_phone, body, status, created_at) "
            "VALUES (:mid, :tid, :dir, :from_, :to_, :body, :status, :now) "
            "ON CONFLICT (message_id) DO NOTHING"
        ),
        {
            "mid": message_id,
            "tid": tenant_id,
            "dir": direction,
            "from_": from_phone,
            "to_": to_phone,
            "body": body,
            "status": status,
            "now": _utcnow(),
        },
    )
    db.commit()


def _send_reply(
    *,
    api_key: str,
    from_number: str,
    to_number: str,
    text_body: str,
    messaging_profile_id: str | None,
    tenant_id: str | None,
    db: Session,
) -> None:
    try:
        resp = send_sms(
            api_key=api_key,
            from_number=from_number,
            to_number=to_number,
            text=text_body,
            messaging_profile_id=messaging_profile_id,
        )
        mid = (resp.get("data") or {}).get("id") or str(uuid.uuid4())
        _log_sms(db, mid, tenant_id, "OUT", from_number, to_number, text_body, "sent")
    except TelnyxApiError as exc:
        logger.error(
            "telnyx_sms_reply_failed from=%s to=%s error=%s",
            from_number, to_number, exc,
        )


@router.post("/webhooks/telnyx/sms")
async def telnyx_sms_webhook(
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
        logger.warning("telnyx_sms_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="invalid_telnyx_signature")

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    data = payload.get("data", {})
    event_id: str = data.get("id") or str(uuid.uuid4())
    event_type: str = data.get("event_type", "")
    ep = data.get("payload", {})

    to_number: str = ep.get("to", [{}])[0].get("phone_number", "") if isinstance(ep.get("to"), list) else ep.get("to", "")
    from_number: str = ep.get("from", {}).get("phone_number", "") if isinstance(ep.get("from"), dict) else ep.get("from", "")
    body_text: str = (ep.get("text") or "").strip()
    message_id: str = ep.get("id") or event_id

    tenant_id = _resolve_tenant_by_did(db, to_number)

    inserted = _insert_event(db, event_id, event_type, tenant_id, payload)
    if not inserted:
        logger.info("telnyx_sms_duplicate event_id=%s", event_id)
        return {"status": "duplicate"}

    logger.info(
        "telnyx_sms event_type=%s event_id=%s from=%s to=%s tenant_id=%s",
        event_type, event_id, from_number, to_number, tenant_id,
    )

    if event_type == "message.received":
        _log_sms(db, message_id, tenant_id, "IN", from_number, to_number, body_text, "received")

        api_key = settings.telnyx_api_key
        if not api_key:
            logger.error("telnyx_sms TELNYX_API_KEY not configured")
            return {"status": "ok"}

        keyword = body_text.upper().split()[0] if body_text else ""

        if keyword in STOP_KEYWORDS:
            if tenant_id:
                _upsert_opt_out(db, tenant_id, from_number, source="sms_stop")
            logger.info("telnyx_sms_opt_out phone=%s tenant_id=%s", from_number, tenant_id)
            _send_reply(
                api_key=api_key,
                from_number=to_number,
                to_number=from_number,
                text_body="You will no longer receive texts. Reply HELP for help.",
                messaging_profile_id=settings.telnyx_messaging_profile_id or None,
                tenant_id=tenant_id,
                db=db,
            )

        elif keyword in HELP_KEYWORDS:
            tenant_info = _get_tenant_info(db, tenant_id) if tenant_id else {"name": "EMS Agency", "billing_phone": ""}
            agency_name = tenant_info["name"]
            billing_phone = tenant_info["billing_phone"] or "our billing office"
            _send_reply(
                api_key=api_key,
                from_number=to_number,
                to_number=from_number,
                text_body=f"Billing help for {agency_name}. Call {billing_phone}. Reply STOP to stop.",
                messaging_profile_id=settings.telnyx_messaging_profile_id or None,
                tenant_id=tenant_id,
                db=db,
            )

        else:
            logger.info("telnyx_sms_unhandled_inbound from=%s body=%.50s", from_number, body_text)

    db.execute(
        text("UPDATE telnyx_events SET processed_at = :now WHERE event_id = :eid"),
        {"now": _utcnow(), "eid": event_id},
    )
    db.commit()

    return {"status": "ok"}
