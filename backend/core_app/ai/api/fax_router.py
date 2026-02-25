from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1", tags=['Fax'])


@router.post("/send")
async def send(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="fax_jobs", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/webhooks/telnyx/fax/inbound", include_in_schema=False)
async def inbound(payload: dict[str, Any], request: Request, db: Session = Depends(db_session_dependency)):
    # idempotent by event_id if provided
    tenant_id = uuid.UUID(payload.get("tenant_id"))
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="fax_events", tenant_id=tenant_id, actor_user_id=None, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

