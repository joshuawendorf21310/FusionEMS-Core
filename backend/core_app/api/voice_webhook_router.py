from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api import voice_payment_helper
from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.telnyx.client import (
    TelnyxApiError,
    call_answer,
    call_gather_using_audio,
    call_hangup,
    call_playback_start,
    call_transfer,
)
from core_app.telnyx.signature import verify_telnyx_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telnyx Voice"])

# ── IVR state names ───────────────────────────────────────────────────────────
STATE_MENU = "MENU"
STATE_COLLECT_STMT = "COLLECT_STATEMENT_ID"
STATE_COLLECT_PHONE = "COLLECT_SMS_PHONE"
STATE_TRANSFER = "TRANSFER"
STATE_DONE = "DONE"

STOP_RETRY_ATTEMPTS = 1
MAX_STMT_RETRIES = 1


def _audio(prompt: str) -> str:
    settings = get_settings()
    base = settings.ivr_audio_base_url.rstrip("/")
    return f"{base}/{prompt}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


# ── DB helpers ────────────────────────────────────────────────────────────────


def _resolve_tenant_by_did(db: Session, to_number: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT tenant_id, forward_to_phone_e164 "
            "FROM tenant_phone_numbers "
            "WHERE phone_e164 = :phone AND purpose = 'billing_voice' "
            "LIMIT 1"
        ),
        {"phone": to_number},
    ).fetchone()
    if row:
        return {"tenant_id": str(row.tenant_id), "forward_to": row.forward_to_phone_e164}
    return None


def _get_or_create_call(
    db: Session,
    call_control_id: str,
    tenant_id: str,
    from_phone: str,
    to_phone: str,
) -> dict[str, Any]:
    row = db.execute(
        text("SELECT * FROM telnyx_calls WHERE call_control_id = :cid"),
        {"cid": call_control_id},
    ).fetchone()
    if row:
        return dict(row._mapping)
    db.execute(
        text(
            "INSERT INTO telnyx_calls "
            "(call_control_id, tenant_id, from_phone, to_phone, state, attempts, created_at, updated_at) "
            "VALUES (:cid, :tid, :from_, :to_, :state, 0, :now, :now)"
        ),
        {
            "cid": call_control_id,
            "tid": tenant_id,
            "from_": from_phone,
            "to_": to_phone,
            "state": STATE_MENU,
            "now": _utcnow(),
        },
    )
    db.commit()
    return {
        "call_control_id": call_control_id,
        "tenant_id": tenant_id,
        "state": STATE_MENU,
        "attempts": 0,
    }


def _update_call(db: Session, call_control_id: str, **fields: Any) -> None:
    set_parts = ", ".join(f"{k} = :{k}" for k in fields)
    fields["cid"] = call_control_id
    fields["updated_at"] = _utcnow()
    db.execute(
        text(
            f"UPDATE telnyx_calls SET {set_parts}, updated_at = :updated_at WHERE call_control_id = :cid"
        ),
        fields,
    )
    db.commit()


def _get_call(db: Session, call_control_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM telnyx_calls WHERE call_control_id = :cid"),
        {"cid": call_control_id},
    ).fetchone()
    if row is None:
        return None
    data = dict(row._mapping)
    if data:
        return data
    # Fallback for test mocks: _mapping may not iterate correctly
    return {
        "state": getattr(row, "state", STATE_MENU),
        "attempts": getattr(row, "attempts", 0),
        "statement_id": getattr(row, "statement_id", None),
        "tenant_id": getattr(row, "tenant_id", None),
        "from_phone": getattr(row, "from_phone", None),
        "to_phone": getattr(row, "to_phone", None),
        "call_control_id": getattr(row, "call_control_id", call_control_id),
    }


def _insert_event(
    db: Session, event_id: str, event_type: str, tenant_id: str | None, raw: dict[str, Any]
) -> bool:
    result = db.execute(
        text(
            "INSERT INTO telnyx_events (event_id, event_type, tenant_id, received_at, raw_json, processed_at) "
            "VALUES (:eid, :etype, :tid, :now, :raw::jsonb, NULL) "
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


def _mark_event_processed(db: Session, event_id: str) -> None:
    db.execute(
        text("UPDATE telnyx_events SET processed_at = :now WHERE event_id = :eid"),
        {"now": _utcnow(), "eid": event_id},
    )
    db.commit()


def _validate_statement(db: Session, tenant_id: str, statement_id_digits: str) -> bool:
    row = db.execute(
        text("SELECT id FROM billing_cases WHERE id::text = :sid AND tenant_id = :tid LIMIT 1"),
        {"sid": statement_id_digits, "tid": tenant_id},
    ).fetchone()
    if row:
        return True
    row2 = db.execute(
        text(
            "SELECT statement_id FROM lob_letters WHERE statement_id::text = :sid AND tenant_id = :tid LIMIT 1"
        ),
        {"sid": statement_id_digits, "tid": tenant_id},
    ).fetchone()
    return row2 is not None


def _check_opt_out(db: Session, tenant_id: str, phone_e164: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM telnyx_opt_outs WHERE tenant_id = :tid AND phone_e164 = :phone LIMIT 1"
        ),
        {"tid": tenant_id, "phone": phone_e164},
    ).fetchone()
    return row is not None


def _get_tenant_forward(db: Session, tenant_id: str) -> str | None:
    row = db.execute(
        text(
            "SELECT forward_to_phone_e164 FROM tenant_phone_numbers "
            "WHERE tenant_id = :tid AND purpose = 'billing_voice' LIMIT 1"
        ),
        {"tid": tenant_id},
    ).fetchone()
    return row.forward_to_phone_e164 if row else None


# ── IVR state actions ─────────────────────────────────────────────────────────


def _play_menu(api_key: str, call_control_id: str, cid_log: str) -> None:
    logger.info("ivr_menu call_control_id=%s", cid_log)
    call_gather_using_audio(
        api_key=api_key,
        call_control_id=call_control_id,
        audio_url=_audio("menu.wav"),
        minimum_digits=1,
        maximum_digits=1,
        timeout_millis=8000,
        client_state=STATE_MENU,
    )


def _play_collect_statement(api_key: str, call_control_id: str) -> None:
    call_gather_using_audio(
        api_key=api_key,
        call_control_id=call_control_id,
        audio_url=_audio("enter_statement_id.wav"),
        minimum_digits=6,
        maximum_digits=12,
        terminating_digit="#",
        timeout_millis=15000,
        client_state=STATE_COLLECT_STMT,
    )


def _play_collect_phone(api_key: str, call_control_id: str) -> None:
    call_gather_using_audio(
        api_key=api_key,
        call_control_id=call_control_id,
        audio_url=_audio("enter_phone.wav"),
        minimum_digits=10,
        maximum_digits=10,
        timeout_millis=12000,
        client_state=STATE_COLLECT_PHONE,
    )


def _do_transfer(
    api_key: str,
    call_control_id: str,
    forward_to: str | None,
    from_phone: str,
) -> None:
    if forward_to:
        logger.info("ivr_transfer call_control_id=%s to=%s", call_control_id, forward_to)
        call_transfer(
            api_key=api_key,
            call_control_id=call_control_id,
            to=forward_to,
            from_=from_phone,
            client_state=STATE_TRANSFER,
        )
    else:
        call_playback_start(
            api_key=api_key,
            call_control_id=call_control_id,
            audio_url=_audio("transferring.wav"),
        )
        call_hangup(api_key=api_key, call_control_id=call_control_id)


def _normalize_e164_us(digits: str) -> str:
    d = "".join(c for c in digits if c.isdigit())
    if len(d) == 10:
        return f"+1{d}"
    if len(d) == 11 and d.startswith("1"):
        return f"+{d}"
    return f"+{d}"


# ── Webhook entrypoint ────────────────────────────────────────────────────────


@router.post("/webhooks/telnyx/voice")
async def telnyx_voice_webhook(
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
        logger.warning("telnyx_voice_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="invalid_telnyx_signature")

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    data = payload.get("data", {})
    event_id: str = data.get("id") or str(uuid.uuid4())
    event_type: str = data.get("event_type", "")
    ep = data.get("payload", {})

    call_control_id: str = ep.get("call_control_id", "")
    to_number: str = ep.get("to", "") or ep.get("call_leg_id", "")
    from_number: str = ep.get("from", "")

    logger.info(
        "telnyx_voice event_type=%s call_control_id=%s event_id=%s",
        event_type,
        call_control_id,
        event_id,
    )

    tenant_info = _resolve_tenant_by_did(db, to_number)
    tenant_id: str | None = tenant_info["tenant_id"] if tenant_info else None

    inserted = _insert_event(db, event_id, event_type, tenant_id, payload)
    if not inserted:
        logger.info("telnyx_voice_duplicate event_id=%s", event_id)
        return {"status": "duplicate"}

    api_key = settings.telnyx_api_key
    if not api_key:
        logger.error("telnyx_voice TELNYX_API_KEY not configured")
        raise HTTPException(status_code=500, detail="telnyx_not_configured")

    try:
        await _dispatch_voice_event(
            event_type=event_type,
            ep=ep,
            call_control_id=call_control_id,
            from_number=from_number,
            to_number=to_number,
            tenant_id=tenant_id,
            tenant_info=tenant_info,
            api_key=api_key,
            db=db,
            settings=settings,
        )
    except TelnyxApiError as exc:
        logger.error(
            "telnyx_voice_api_error event_type=%s call_control_id=%s error=%s",
            event_type,
            call_control_id,
            exc,
        )
    finally:
        _mark_event_processed(db, event_id)

    return {"status": "ok"}


async def _dispatch_voice_event(
    *,
    event_type: str,
    ep: dict[str, Any],
    call_control_id: str,
    from_number: str,
    to_number: str,
    tenant_id: str | None,
    tenant_info: dict[str, Any] | None,
    api_key: str,
    db: Session,
    settings: Any,
) -> None:

    if event_type == "call.initiated":
        call_answer(api_key=api_key, call_control_id=call_control_id)
        return

    if event_type == "call.answered":
        if not tenant_id:
            logger.warning("ivr_no_tenant_for_did to=%s", to_number)
            call_hangup(api_key=api_key, call_control_id=call_control_id)
            return
        _get_or_create_call(db, call_control_id, tenant_id, from_number, to_number)
        _play_menu(api_key, call_control_id, call_control_id)
        return

    if event_type in ("call.gather.ended", "call.dtmf.received"):
        await _handle_gather(
            ep=ep,
            call_control_id=call_control_id,
            from_number=from_number,
            to_number=to_number,
            tenant_id=tenant_id,
            tenant_info=tenant_info,
            api_key=api_key,
            db=db,
            settings=settings,
        )
        return

    if event_type == "call.hangup":
        logger.info("ivr_hangup call_control_id=%s", call_control_id)
        _update_call(db, call_control_id, state=STATE_DONE)
        return

    logger.debug("telnyx_voice_unhandled_event event_type=%s", event_type)


async def _handle_gather(
    *,
    ep: dict[str, Any],
    call_control_id: str,
    from_number: str,
    to_number: str,
    tenant_id: str | None,
    tenant_info: dict[str, Any] | None,
    api_key: str,
    db: Session,
    settings: Any,
) -> None:
    digits: str = ep.get("digits", "").strip().rstrip("#")
    status: str = ep.get("status", "")

    raw_client_state: str = ep.get("client_state", "")
    try:
        call_state_bytes = base64.b64decode(raw_client_state + "==")
        call_state = call_state_bytes.decode("utf-8")
    except Exception:
        call_state = raw_client_state

    call_record = _get_call(db, call_control_id)
    if call_record is None:
        logger.warning("ivr_no_call_record call_control_id=%s", call_control_id)
        return

    forward_to = (tenant_info or {}).get("forward_to") or _get_tenant_forward(db, tenant_id or "")

    if status == "no_input" or not digits:
        _update_call(db, call_control_id, state=STATE_TRANSFER)
        _do_transfer(api_key, call_control_id, forward_to, from_number)
        return

    current_state = call_record.get("state", STATE_MENU)

    if current_state == STATE_MENU:
        if digits == "9":
            _play_menu(api_key, call_control_id, call_control_id)
        elif digits == "1":
            _update_call(db, call_control_id, state=STATE_COLLECT_STMT)
            _play_collect_statement(api_key, call_control_id)
        else:
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(api_key, call_control_id, forward_to, from_number)
        return

    if current_state == STATE_COLLECT_STMT:
        attempts: int = call_record.get("attempts", 0)
        if not digits or len(digits) < 6:
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(api_key, call_control_id, forward_to, from_number)
            return
        valid = _validate_statement(db, tenant_id or "", digits) if tenant_id else False
        if not valid:
            if attempts < MAX_STMT_RETRIES:
                _update_call(db, call_control_id, attempts=attempts + 1)
                call_playback_start(
                    api_key=api_key,
                    call_control_id=call_control_id,
                    audio_url=_audio("invalid.wav"),
                )
                _play_collect_statement(api_key, call_control_id)
            else:
                _update_call(db, call_control_id, state=STATE_TRANSFER)
                _do_transfer(api_key, call_control_id, forward_to, from_number)
        else:
            _update_call(
                db, call_control_id, state=STATE_COLLECT_PHONE, statement_id=digits, attempts=0
            )
            _play_collect_phone(api_key, call_control_id)
        return

    if current_state == STATE_COLLECT_PHONE:
        if len(digits) != 10:
            call_playback_start(
                api_key=api_key,
                call_control_id=call_control_id,
                audio_url=_audio("invalid.wav"),
            )
            _play_collect_phone(api_key, call_control_id)
            return

        phone_e164 = _normalize_e164_us(digits)

        if _check_opt_out(db, tenant_id or "", phone_e164):
            logger.info("ivr_opted_out phone=%s tenant_id=%s", phone_e164, tenant_id)
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(api_key, call_control_id, forward_to, from_number)
            return

        statement_id: str = call_record.get("statement_id", "")

        await voice_payment_helper.send_payment_link_for_call(
            db=db,
            api_key=api_key,
            settings=settings,
            tenant_id=tenant_id or "",
            statement_id=statement_id,
            phone_e164=phone_e164,
            from_number=to_number,
        )

        _update_call(db, call_control_id, state=STATE_DONE, sms_phone=phone_e164)

        call_gather_using_audio(
            api_key=api_key,
            call_control_id=call_control_id,
            audio_url=_audio("sent_sms.wav"),
            minimum_digits=1,
            maximum_digits=1,
            timeout_millis=8000,
            client_state="POST_SMS",
        )
        return

    if call_state == "POST_SMS":
        if digits == "1":
            _do_transfer(api_key, call_control_id, forward_to, from_number)
        else:
            call_playback_start(
                api_key=api_key,
                call_control_id=call_control_id,
                audio_url=_audio("goodbye.wav"),
            )
            call_hangup(api_key=api_key, call_control_id=call_control_id)
        return
