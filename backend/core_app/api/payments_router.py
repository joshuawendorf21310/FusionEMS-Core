from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.payments.stripe_service import (
    StripeConfig,
    StripeNotConfigured,
    create_connect_checkout_session,
)
from core_app.schemas.auth import CurrentUser
from core_app.telnyx.client import TelnyxApiError, send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing/payments", tags=["Billing Payments"])

_E164_US_RE = re.compile(r"^\+1[2-9]\d{9}$")


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _get_connected_account(db: Session, tenant_id: str) -> str | None:
    row = db.execute(
        text("SELECT stripe_connected_account_id FROM tenants WHERE id = :tid LIMIT 1"),
        {"tid": tenant_id},
    ).fetchone()
    return row.stripe_connected_account_id if row else None


def _is_opted_out(db: Session, tenant_id: str, phone_e164: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM telnyx_opt_outs WHERE tenant_id = :tid AND phone_e164 = :phone LIMIT 1"
        ),
        {"tid": tenant_id, "phone": phone_e164},
    ).fetchone()
    return row is not None


def _log_sms_out(
    db: Session, tenant_id: str, from_phone: str, to_phone: str, body: str, message_id: str
) -> None:
    db.execute(
        text(
            "INSERT INTO telnyx_sms_messages "
            "(message_id, tenant_id, direction, from_phone, to_phone, body, status, created_at) "
            "VALUES (:mid, :tid, 'OUT', :from_, :to_, :body, 'sent', :now) "
            "ON CONFLICT (message_id) DO NOTHING"
        ),
        {
            "mid": message_id,
            "tid": tenant_id,
            "from_": from_phone,
            "to_": to_phone,
            "body": body,
            "now": _utcnow(),
        },
    )
    db.commit()


# ── POST /checkout-session ────────────────────────────────────────────────────


class CheckoutSessionRequest(BaseModel):
    tenant_id: uuid.UUID
    statement_id: str
    amount_cents: int
    currency: str = "usd"
    patient_display_name: str | None = None

    @field_validator("amount_cents")
    @classmethod
    def _positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_cents must be positive")
        return v


@router.post("/checkout-session")
async def create_checkout_session(
    body: CheckoutSessionRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    if str(body.tenant_id) != str(current.tenant_id) and current.role not in ("founder", "admin"):
        raise HTTPException(status_code=403, detail="tenant_mismatch")

    settings = get_settings()
    connected_account_id = _get_connected_account(db, str(body.tenant_id))
    if not connected_account_id:
        raise HTTPException(status_code=422, detail="tenant_stripe_account_not_configured")

    cfg = StripeConfig(secret_key=settings.stripe_secret_key)
    success_url = f"{settings.api_base_url}/pay/success?statement_id={body.statement_id}"
    cancel_url = f"{settings.api_base_url}/pay/cancel?statement_id={body.statement_id}"

    try:
        result = create_connect_checkout_session(
            cfg=cfg,
            connected_account_id=connected_account_id,
            amount_cents=body.amount_cents,
            currency=body.currency,
            statement_id=body.statement_id,
            tenant_id=str(body.tenant_id),
            patient_account_ref=body.patient_display_name,
            lob_letter_id=None,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "checkout_url": result["checkout_url"],
        "stripe_checkout_session_id": result["checkout_session_id"],
        "connected_account_id": connected_account_id,
    }


# ── POST /send-link-sms ───────────────────────────────────────────────────────


class SendLinkSmsRequest(BaseModel):
    tenant_id: uuid.UUID
    to_phone_e164: str
    checkout_url: str
    statement_id: str

    @field_validator("to_phone_e164")
    @classmethod
    def _valid_e164(cls, v: str) -> str:
        if not _E164_US_RE.match(v):
            raise ValueError(f"to_phone_e164 must be a valid US E.164 number, got: {v!r}")
        return v


@router.post("/send-link-sms")
async def send_link_sms(
    body: SendLinkSmsRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    if str(body.tenant_id) != str(current.tenant_id) and current.role not in ("founder", "admin"):
        raise HTTPException(status_code=403, detail="tenant_mismatch")

    settings = get_settings()

    if _is_opted_out(db, str(body.tenant_id), body.to_phone_e164):
        raise HTTPException(status_code=422, detail="phone_opted_out")

    from_number = settings.telnyx_from_number
    if not from_number:
        raise HTTPException(status_code=503, detail="telnyx_from_number_not_configured")

    sms_text = (
        f"Pay your medical transport balance online (secure): {body.checkout_url} "
        f"Statement #{body.statement_id} — Reply STOP to opt out."
    )

    api_key = settings.telnyx_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="telnyx_not_configured")

    try:
        resp = send_sms(
            api_key=api_key,
            from_number=from_number,
            to_number=body.to_phone_e164,
            text=sms_text,
            messaging_profile_id=settings.telnyx_messaging_profile_id or None,
        )
        message_id = (resp.get("data") or {}).get("id") or str(uuid.uuid4())
        _log_sms_out(db, str(body.tenant_id), from_number, body.to_phone_e164, sms_text, message_id)
        logger.info(
            "payment_sms_sent statement_id=%s to=%s message_id=%s",
            body.statement_id,
            body.to_phone_e164,
            message_id,
        )
    except TelnyxApiError as exc:
        logger.error("payment_sms_failed to=%s error=%s", body.to_phone_e164, exc)
        raise HTTPException(status_code=502, detail=f"telnyx_send_failed: {exc}")

    return {"status": "sent", "message_id": message_id}
