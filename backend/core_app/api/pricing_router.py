from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.payments.stripe_service import StripeConfig, verify_webhook_signature, StripeNotConfigured
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.realtime_events import emit_payment_confirmed

router = APIRouter(prefix="/api/v1", tags=["Pricing"])


@router.post("/public/roi/calc", include_in_schema=True)
async def roi(payload: dict[str, Any], request: Request):
    calls = float(payload.get("calls_per_month", 0))
    avg = float(payload.get("avg_reimbursement", 0))
    return {"estimated_revenue": calls * avg, "assumptions": payload}


@router.post("/public/signup/start", include_in_schema=True)
async def signup(payload: dict[str, Any], request: Request, db: Session = Depends(db_session_dependency)):
    # Provisioning workflow lives in founder/tenancy module; this endpoint returns
    # an integration-ready response.
    return {"status": "ok", "next": "stripe_checkout"}


@router.post("/public/webhooks/stripe", include_in_schema=True)
async def stripe_webhook(request: Request, db: Session = Depends(db_session_dependency)):
    """
    Stripe webhook endpoint. Idempotent by Stripe event id. Stores receipts in stripe_webhook_receipts.
    """
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
    tenant_id = (event.get("data", {}).get("object", {}).get("metadata", {}) or {}).get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="missing_tenant_id_metadata")

    svc = DominationService(db, get_event_publisher())
    # idempotency check
    existing = svc.repo("stripe_webhook_receipts").list(tenant_id, limit=2000)
    if any(r["data"].get("event_id") == event_id for r in existing):
        return {"status": "duplicate", "event_id": event_id}

    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    row = await svc.create(
        table="stripe_webhook_receipts",
        tenant_id=tenant_id,
        actor_user_id=None,
        data={"event_id": event_id, "payload_hash": payload_hash, "event": event},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    event_type = event.get("type") or event.get("event_type") or ""
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

    return {"status": "ok", "receipt_id": row["id"], "event_id": event_id}


@router.post("/billing/subscription/usage/push")
async def usage_push(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="usage_records", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state, "correlation_id", None))
