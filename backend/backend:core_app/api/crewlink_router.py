from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/crewlink", tags=['CrewLink'])


@router.post("/page")
async def create_page(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="pages", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/respond")
async def respond(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="page_responses", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/pages/active")
async def active(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency), limit: int = 50, offset: int = 0):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("pages").list(tenant_id=current.tenant_id, limit=limit, offset=offset)

@router.post("/availability/me")
async def availability(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = dict(payload)
    data["user_id"] = str(current.user_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="availability_blocks", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

