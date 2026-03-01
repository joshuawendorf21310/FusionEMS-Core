from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.billing.statement_pdf import (
    TEMPLATE_VERSION,
    StatementContext,
    generate_billing_statement_pdf,
)
from core_app.core.config import get_settings
from core_app.fax.telnyx_service import TelnyxConfig, send_sms
from core_app.integrations.lob_service import (
    LobNotConfigured,
    _get_lob_config,
    send_statement_letter,
)
from core_app.payments.stripe_service import (
    StripeConfig,
    StripeNotConfigured,
    create_connect_checkout_session,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Statements - Billing"])

E164_RE = re.compile(r"^\+1[2-9]\d{9}$")



# ── Schemas ───────────────────────────────────────────────────────────────────

class MailStatementRequest(BaseModel):
    patient_name: str
    patient_address: dict[str, str]
    agency_address: dict[str, str]
    agency_phone: str
    incident_date: str
    transport_date: str
    service_lines: list[dict[str, Any]]
    amount_due_cents: int
    amount_paid_cents: int = 0
    patient_account_ref: str | None = None


class PayStatementRequest(BaseModel):
    patient_account_ref: str | None = None


class PaySmsRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not E164_RE.match(v):
            raise ValueError("phone_number must be E.164 US number e.g. +14155551234")
        return v


# ── Helper ────────────────────────────────────────────────────────────────────

def _load_statement(svc: DominationService, statement_id: uuid.UUID, tenant_id: uuid.UUID) -> dict[str, Any]:
    rec = svc.repo("billing_cases").get(tenant_id=tenant_id, record_id=statement_id)
    if not rec:
        raise HTTPException(status_code=404, detail="statement_not_found")
    return rec


def _load_tenant_stripe_account(db: Session, tenant_id: uuid.UUID) -> str:
    from sqlalchemy import text
    row = db.execute(
        text("SELECT data->>'stripe_connected_account_id' AS acct FROM tenants WHERE id = :tid LIMIT 1"),
        {"tid": str(tenant_id)},
    ).mappings().first()
    if not row or not row["acct"]:
        raise HTTPException(status_code=422, detail="tenant_stripe_account_not_connected")
    return row["acct"]


# ── POST /statements/{statement_id}/mail ─────────────────────────────────────

@router.post("/statements/{statement_id}/mail", status_code=201)
async def mail_statement(
    statement_id: uuid.UUID,
    body: MailStatementRequest,
    request: Request,
    current: CurrentUser = Depends(require_role("billing", "agency_admin", "founder")),
    db: Session = Depends(db_session_dependency),
):
    """
    Generate PDF, compute SHA-256 BEFORE sending to Lob, create letter, persist outbound log.
    """
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    settings = get_settings()

    # Build pay URL (statement must already have a checkout link or we generate on-demand)
    pay_url = f"{settings.api_base_url}/api/v1/statements/{statement_id}/pay"

    ctx = StatementContext(
        statement_id=str(statement_id),
        tenant_id=str(current.tenant_id),
        patient_name=body.patient_name,
        patient_address=body.patient_address,
        agency_name=body.agency_address.get("agency_name") or body.agency_address.get("name", ""),
        agency_address=body.agency_address,
        agency_phone=body.agency_phone,
        incident_date=body.incident_date,
        transport_date=body.transport_date,
        service_lines=body.service_lines,
        amount_due_cents=body.amount_due_cents,
        amount_paid_cents=body.amount_paid_cents,
        pay_url=pay_url,
    )

    # Generate PDF + SHA-256 (hash computed before Lob upload)
    try:
        pdf_bytes, outbound_sha256 = generate_billing_statement_pdf(ctx)
    except Exception as exc:
        logger.error("pdf_generation_failed statement_id=%s error=%s", statement_id, exc)
        raise HTTPException(status_code=500, detail=f"pdf_generation_failed: {exc}")

    from_address = {
        "name": body.agency_address.get("agency_name") or body.agency_address.get("name", ""),
        "line1": body.agency_address.get("line1", ""),
        "line2": body.agency_address.get("line2", ""),
        "city": body.agency_address.get("city", ""),
        "state": body.agency_address.get("state", ""),
        "zip": body.agency_address.get("zip", ""),
    }
    to_address = {
        "name": body.patient_name,
        **body.patient_address,
    }

    try:
        _get_lob_config()
        lob_resp = send_statement_letter(
            pdf_bytes=pdf_bytes,
            outbound_sha256=outbound_sha256,
            statement_id=str(statement_id),
            template_version=TEMPLATE_VERSION,
            to_address=to_address,
            from_address=from_address,
        )
    except LobNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("lob_send_failed statement_id=%s error=%s", statement_id, exc)
        raise HTTPException(status_code=502, detail=f"lob_error: {exc}")

    lob_letter_id: str = lob_resp.get("id", "")

    # Persist outbound log
    log_rec = await svc.create(
        table="lob_letters",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "statement_id": str(statement_id),
            "lob_letter_id": lob_letter_id,
            "outbound_pdf_sha256": outbound_sha256,
            "template_version": TEMPLATE_VERSION,
            "lob_response": lob_resp,
            "status": "created",
            "created_at": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    await publisher.publish(
        "statement.mailed",
        tenant_id=current.tenant_id,
        entity_id=statement_id,
        payload={"lob_letter_id": lob_letter_id, "outbound_sha256": outbound_sha256},
        entity_type="statement",
        correlation_id=correlation_id,
    )

    return {
        "status": "mailed",
        "statement_id": str(statement_id),
        "lob_letter_id": lob_letter_id,
        "outbound_pdf_sha256": outbound_sha256,
        "template_version": TEMPLATE_VERSION,
        "log_record_id": log_rec["id"],
    }


# ── POST /statements/{statement_id}/pay ──────────────────────────────────────

@router.post("/statements/{statement_id}/pay")
async def create_payment_session(
    statement_id: uuid.UUID,
    body: PayStatementRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Create Stripe Checkout Session on the agency's connected account.
    Payment flows directly to the agency; FusionEMS is not the merchant of record.
    """
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    statement = _load_statement(svc, statement_id, current.tenant_id)
    data: dict[str, Any] = statement.get("data", {})

    amount_due_cents: int = data.get("amount_due_cents", 0)
    if amount_due_cents <= 0:
        raise HTTPException(status_code=422, detail="statement_balance_zero")

    connected_account_id = _load_tenant_stripe_account(db, current.tenant_id)

    lob_letter_id: str | None = data.get("lob_letter_id")

    settings = get_settings()
    cfg = StripeConfig(
        secret_key=settings.stripe_secret_key,
        webhook_secret=settings.stripe_webhook_secret,
    )

    try:
        result = create_connect_checkout_session(
            cfg=cfg,
            connected_account_id=connected_account_id,
            amount_cents=amount_due_cents,
            statement_id=str(statement_id),
            tenant_id=str(current.tenant_id),
            patient_account_ref=body.patient_account_ref or data.get("patient_account_ref"),
            lob_letter_id=lob_letter_id,
            success_url=f"{settings.api_base_url}/patient/pay/success?stmt={statement_id}",
            cancel_url=f"{settings.api_base_url}/patient/pay/cancel?stmt={statement_id}",
        )
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("stripe_checkout_failed statement_id=%s error=%s", statement_id, exc)
        raise HTTPException(status_code=502, detail=f"stripe_error: {exc}")

    # Persist payment link record
    await svc.create(
        table="patient_payment_links",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "statement_id": str(statement_id),
            "checkout_session_id": result["checkout_session_id"],
            "checkout_url": result["checkout_url"],
            "connected_account_id": connected_account_id,
            "amount_cents": amount_due_cents,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    return {
        "checkout_url": result["checkout_url"],
        "checkout_session_id": result["checkout_session_id"],
        "statement_id": str(statement_id),
        "amount_cents": amount_due_cents,
    }


# ── POST /statements/{statement_id}/pay/sms ──────────────────────────────────

@router.post("/statements/{statement_id}/pay/sms", status_code=202)
async def send_payment_sms(
    statement_id: uuid.UUID,
    body: PaySmsRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Generate a Stripe Checkout Session (if not already present) and SMS the
    checkout URL to the patient's phone via Telnyx.
    Card data never enters FusionEMS systems.
    """
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    statement = _load_statement(svc, statement_id, current.tenant_id)
    data: dict[str, Any] = statement.get("data", {})
    amount_due_cents: int = data.get("amount_due_cents", 0)
    if amount_due_cents <= 0:
        raise HTTPException(status_code=422, detail="statement_balance_zero")

    connected_account_id = _load_tenant_stripe_account(db, current.tenant_id)

    settings = get_settings()
    cfg = StripeConfig(
        secret_key=settings.stripe_secret_key,
        webhook_secret=settings.stripe_webhook_secret,
    )

    try:
        checkout = create_connect_checkout_session(
            cfg=cfg,
            connected_account_id=connected_account_id,
            amount_cents=amount_due_cents,
            statement_id=str(statement_id),
            tenant_id=str(current.tenant_id),
            patient_account_ref=data.get("patient_account_ref"),
            lob_letter_id=data.get("lob_letter_id"),
            success_url=f"{settings.api_base_url}/patient/pay/success?stmt={statement_id}",
            cancel_url=f"{settings.api_base_url}/patient/pay/cancel?stmt={statement_id}",
        )
    except Exception as exc:
        logger.error("sms_checkout_create_failed statement_id=%s error=%s", statement_id, exc)
        raise HTTPException(status_code=502, detail=f"stripe_error: {exc}")

    checkout_url: str = checkout["checkout_url"]
    amount_fmt = f"${amount_due_cents / 100:,.2f}"

    telnyx_cfg = TelnyxConfig(
        api_key=settings.telnyx_api_key,
        messaging_profile_id=settings.telnyx_messaging_profile_id or None,
    )
    sms_text = (
        f"FusionEMS: Your medical transport balance of {amount_fmt} is due. "
        f"Pay securely here: {checkout_url} "
        f"(Ref: {str(statement_id)[:8]})"
    )
    try:
        send_sms(
            cfg=telnyx_cfg,
            from_number=settings.telnyx_from_number,
            to_number=body.phone_number,
            text=sms_text,
        )
    except Exception as exc:
        logger.error("telnyx_sms_failed statement_id=%s phone=%s error=%s",
                     statement_id, body.phone_number[:6] + "****", exc)
        raise HTTPException(status_code=502, detail=f"sms_send_failed: {exc}")

    logger.info(
        "payment_sms_sent statement_id=%s phone=%.6s**** amount=%s correlation_id=%s",
        statement_id, body.phone_number, amount_fmt, correlation_id,
    )

    return {
        "status": "sms_sent",
        "statement_id": str(statement_id),
        "checkout_session_id": checkout["checkout_session_id"],
        "amount_cents": amount_due_cents,
    }


@router.get("/patient/statements")
async def list_patient_statements(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """List billing statements for the current patient/tenant."""
    from core_app.services.domination_service import DominationService
    from core_app.services.event_publisher import get_event_publisher

    svc = DominationService(db, get_event_publisher())
    rows = svc.repo("ar_statements").list(tenant_id=current.tenant_id, limit=limit, offset=offset)
    return {"statements": rows, "total": len(rows)}
