from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1", tags=['Pricing'])


@router.post("/public/roi/calc", include_in_schema=True)
async def roi(payload: dict[str, Any], request: Request):
    calls = float(payload.get("calls_per_month", 0))
    avg = float(payload.get("avg_reimbursement", 0))
    return {"estimated_revenue": calls*avg, "assumptions": payload}

@router.post("/public/signup/start", include_in_schema=True)
async def signup(payload: dict[str, Any], request: Request, db: Session = Depends(db_session_dependency)):
    # create a pricing plan selection record; actual stripe checkout created in payments integration
    return {"status":"ok","next":"stripe_checkout"}

@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(payload: dict[str, Any], request: Request, db: Session = Depends(db_session_dependency)):
    # idempotency by event id if provided
    tenant_id = uuid.UUID(payload.get("tenant_id")) if payload.get("tenant_id") else None
    if tenant_id is None:
        return {"error":"tenant_id_required"}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="stripe_webhook_receipts", tenant_id=tenant_id, actor_user_id=None, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/billing/subscription/usage/push")
async def usage_push(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="usage_records", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

