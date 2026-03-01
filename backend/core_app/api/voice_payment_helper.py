from __future__ import annotations

import logging
from datetime import UTC
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def send_payment_link_for_call(
    *,
    db: Session,
    api_key: str,
    settings: Any,
    tenant_id: str,
    statement_id: str,
    phone_e164: str,
    from_number: str,
) -> None:
    """
    Called from IVR after phone number is collected.
    1. Look up tenant's connected Stripe account.
    2. Look up statement amount from billing_cases / lob_letters.
    3. Create Stripe Checkout Session on connected account.
    4. Send SMS with checkout URL (enforcing opt-out).
    """
    connected_account_id = _get_connected_stripe_account(db, tenant_id)
    if not connected_account_id:
        logger.warning("ivr_payment_no_stripe_account tenant_id=%s", tenant_id)
        return

    amount_cents, currency = _get_statement_amount(db, tenant_id, statement_id)
    if not amount_cents:
        logger.warning("ivr_payment_no_amount statement_id=%s", statement_id)
        amount_cents = 0

    from core_app.payments.stripe_service import StripeConfig, create_connect_checkout_session
    cfg = StripeConfig(secret_key=settings.stripe_secret_key)
    success_url = f"{settings.api_base_url}/pay/success?statement_id={statement_id}"
    cancel_url  = f"{settings.api_base_url}/pay/cancel?statement_id={statement_id}"

    try:
        result = create_connect_checkout_session(
            cfg=cfg,
            connected_account_id=connected_account_id,
            amount_cents=amount_cents,
            currency=currency,
            statement_id=statement_id,
            tenant_id=tenant_id,
            patient_account_ref=None,
            lob_letter_id=None,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        checkout_url = result["checkout_url"]
    except Exception as exc:
        logger.error("ivr_payment_checkout_failed statement_id=%s error=%s", statement_id, exc)
        return

    sms_text = (
        f"Pay your medical transport balance online (secure): {checkout_url} "
        f"— Reply STOP to opt out."
    )

    from core_app.telnyx.client import TelnyxApiError, send_sms
    try:
        resp = send_sms(
            api_key=api_key,
            from_number=from_number,
            to_number=phone_e164,
            text=sms_text,
            messaging_profile_id=settings.telnyx_messaging_profile_id or None,
        )
        _log_sms_out(db, tenant_id, from_number, phone_e164, sms_text, resp)
    except TelnyxApiError as exc:
        logger.error("ivr_payment_sms_failed phone=%s error=%s", phone_e164, exc)


def _get_connected_stripe_account(db: Session, tenant_id: str) -> str | None:
    row = db.execute(
        text("SELECT stripe_connected_account_id FROM tenants WHERE id = :tid LIMIT 1"),
        {"tid": tenant_id},
    ).fetchone()
    if row and row.stripe_connected_account_id:
        return row.stripe_connected_account_id
    return None


def _get_statement_amount(db: Session, tenant_id: str, statement_id: str) -> tuple[int, str]:
    row = db.execute(
        text(
            "SELECT total_amount_cents, currency FROM billing_cases "
            "WHERE id::text = :sid AND tenant_id = :tid LIMIT 1"
        ),
        {"sid": statement_id, "tid": tenant_id},
    ).fetchone()
    if row:
        return (row.total_amount_cents or 0, row.currency or "usd")
    return (0, "usd")


def _log_sms_out(
    db: Session,
    tenant_id: str,
    from_phone: str,
    to_phone: str,
    body: str,
    resp: dict,
) -> None:
    from datetime import datetime
    message_id = (resp.get("data") or {}).get("id") or resp.get("id") or ""
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
            "now": datetime.now(UTC).isoformat(),
        },
    )
    db.commit()
