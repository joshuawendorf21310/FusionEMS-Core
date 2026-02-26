from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.payments.stripe_service import StripeConfig, verify_webhook_signature, StripeNotConfigured
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1", tags=["Pricing"])


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
    return {"status": "ok", "receipt_id": row["id"], "event_id": event_id}


@router.post("/billing/subscription/usage/push")
async def usage_push(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="usage_records", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state, "correlation_id", None))
