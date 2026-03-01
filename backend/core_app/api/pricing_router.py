from __future__ import annotations

import contextlib
import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.payments.stripe_service import (
    StripeConfig,
    StripeNotConfigured,
    verify_webhook_signature,
)
from core_app.pricing.catalog import calculate_quote
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.realtime_events import emit_payment_confirmed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Pricing"])


@router.post("/public/roi/calc", include_in_schema=True)
async def roi(payload: dict[str, Any], request: Request):
    calls = float(payload.get("calls_per_month", 0))
    avg = float(payload.get("avg_reimbursement", 0))
    return {"estimated_revenue": calls * avg, "assumptions": payload}


@router.post("/public/signup/start", include_in_schema=True)
async def signup(payload: dict[str, Any], request: Request, db: Session = Depends(db_session_dependency)):
    import stripe as stripe_lib

    settings = get_settings()
    system_tenant = settings.system_tenant_id
    try:
        tenant_uuid = uuid.UUID(system_tenant) if system_tenant else uuid.uuid4()
    except Exception:
        tenant_uuid = uuid.uuid4()
    svc = DominationService(db, get_event_publisher())
    application = await svc.create(
        table="onboarding_applications",
        tenant_id=tenant_uuid,
        actor_user_id=None,
        data={
            "agency_name": payload.get("agency_name", ""),
            "contact_email": payload.get("email", ""),
            "agency_type": payload.get("agency_type", ""),
            "annual_call_volume": payload.get("annual_call_volume"),
            "selected_modules": payload.get("modules", []),
            "status": "pending_payment",
            "created_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    application_id = application["id"]

    if not settings.stripe_secret_key:
        return {"status": "ok", "application_id": application_id, "checkout_url": None, "note": "stripe_not_configured"}

    stripe_lib.api_key = settings.stripe_secret_key

    plan_code = str(payload.get("plan_code", "") or "").strip()
    tier_code = str(payload.get("tier_code", "") or "").strip() or None
    billing_tier_code = str(payload.get("billing_tier_code", "") or "").strip() or None
    addon_codes = list(payload.get("addon_codes", payload.get("modules", [])))

    try:
        quote = calculate_quote(
            plan_code=plan_code,
            tier_code=tier_code,
            billing_tier_code=billing_tier_code,
            addon_codes=addon_codes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if quote.requires_quote:
        return {
            "status": "ok",
            "application_id": application_id,
            "checkout_url": None,
            "note": "contact_sales",
        }

    if not quote.stripe_line_items:
        raise HTTPException(status_code=422, detail="No billable line items for this plan configuration")

    agency_name = payload.get("agency_name", "New Agency")
    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"FusionEMS — {agency_name}"},
                "unit_amount": quote.total_monthly_cents,
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }
    ]

    base_url = settings.api_base_url.rstrip("/")
    session = stripe_lib.checkout.Session.create(
        mode="subscription",
        line_items=line_items,
        metadata={"application_id": str(application_id), "source": "public_signup"},
        success_url=f"{base_url}/onboarding/success?application_id={application_id}",
        cancel_url=f"{base_url}/onboarding/cancel?application_id={application_id}",
    )

    return {"status": "ok", "application_id": application_id, "checkout_url": session.url}


@router.post("/public/webhooks/stripe", include_in_schema=True)
async def stripe_webhook(request: Request, db: Session = Depends(db_session_dependency)):
    settings = get_settings()
    payload_bytes = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = verify_webhook_signature(
            cfg=StripeConfig(secret_key=settings.stripe_secret_key, webhook_secret=settings.stripe_webhook_secret or None),
            payload=payload_bytes,
            sig_header=sig,
        )
    except StripeNotConfigured as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_signature")

    event_id = event.get("id")
    metadata = (event.get("data", {}).get("object", {}).get("metadata", {}) or {})
    application_id = metadata.get("application_id")
    tenant_id_meta = metadata.get("tenant_id")

    settings_system_tenant = settings.system_tenant_id
    try:
        system_uuid = uuid.UUID(settings_system_tenant) if settings_system_tenant else uuid.uuid4()
    except Exception:
        system_uuid = uuid.uuid4()

    idempotency_tenant = system_uuid
    if not application_id and tenant_id_meta:
        with contextlib.suppress(Exception):
            idempotency_tenant = uuid.UUID(tenant_id_meta)

    svc = DominationService(db, get_event_publisher())
    existing = svc.repo("stripe_webhook_receipts").list(idempotency_tenant, limit=2000)
    if any(r["data"].get("event_id") == event_id for r in existing):
        return {"status": "duplicate", "event_id": event_id}

    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    row = await svc.create(
        table="stripe_webhook_receipts",
        tenant_id=idempotency_tenant,
        actor_user_id=None,
        data={"event_id": event_id, "payload_hash": payload_hash, "event": event},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    event_type = event.get("type") or event.get("event_type") or ""
    if event_type in ("checkout.session.completed", "payment_intent.succeeded"):
        if application_id:
            await _handle_onboarding_payment(db, application_id, event, request)
        elif tenant_id_meta:
            await _handle_tenant_billing_event(db, tenant_id_meta, event, request)

    return {"status": "ok", "receipt_id": row["id"], "event_id": event_id}


async def _handle_onboarding_payment(
    db: Session,
    application_id: str,
    event: dict,
    request: Request,
) -> None:
    from core_app.services.tenant_provisioning import provision_tenant_from_application

    app_row = db.execute(
        text(
            "SELECT id, agency_name, contact_email, agency_type, annual_call_volume, "
            "selected_modules, legal_status, status, stripe_customer_id, stripe_subscription_id "
            "FROM onboarding_applications WHERE id = :app_id"
        ),
        {"app_id": application_id},
    ).mappings().first()

    if app_row is None:
        logger.warning("Stripe webhook: application %s not found", application_id)
        return

    if app_row["legal_status"] != "signed":
        logger.warning(
            "Stripe webhook: application %s legal_status is '%s', not 'signed'. Skipping provisioning.",
            application_id,
            app_row["legal_status"],
        )
        return

    if app_row["status"] == "provisioned":
        logger.info("Stripe webhook: application %s already provisioned, skipping.", application_id)
        return

    try:
        result = await provision_tenant_from_application(db, application_id, dict(app_row), event)
    except Exception as exc:
        logger.error("provision_tenant_from_application failed for application %s: %s", application_id, exc)
        return

    stripe_obj = event.get("data", {}).get("object", {})
    stripe_customer_id = stripe_obj.get("customer")
    stripe_subscription_id = stripe_obj.get("subscription")
    now = datetime.now(UTC).isoformat()

    db.execute(
        text(
            "UPDATE onboarding_applications SET status = 'provisioned', "
            "stripe_customer_id = :cust, stripe_subscription_id = :sub, "
            "provisioned_at = :now, tenant_id = :tid WHERE id = :app_id"
        ),
        {
            "cust": stripe_customer_id,
            "sub": stripe_subscription_id,
            "now": now,
            "tid": result.get("tenant_id"),
            "app_id": application_id,
        },
    )
    db.commit()
    logger.info("Onboarding provisioning complete for application %s, tenant %s", application_id, result.get("tenant_id"))


async def _handle_tenant_billing_event(
    db: Session,
    tenant_id: str,
    event: dict,
    request: Request,
) -> None:
    event_type = event.get("type") or ""
    if event_type == "payment_intent.succeeded":
        pi_obj = event.get("data", {}).get("object", {})
        amount_cents = pi_obj.get("amount_received") or pi_obj.get("amount") or 0
        pi_id = pi_obj.get("id")
        try:
            tenant_uuid = uuid.UUID(str(tenant_id))
        except Exception:
            tenant_uuid = uuid.uuid4()
        publisher = get_event_publisher()
        await emit_payment_confirmed(
            publisher=publisher,
            tenant_id=tenant_uuid,
            payment_id=uuid.uuid4(),
            amount_cents=int(amount_cents),
            stripe_payment_intent=pi_id,
            correlation_id=getattr(request.state, "correlation_id", None),
        )


@router.post("/billing/subscription/usage/push")
async def usage_push(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="usage_records",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
