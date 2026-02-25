from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/weather", tags=['Weather'])


@router.get("/layers")
async def layers(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # returns provider-agnostic layer templates; configure in integrations
    return {"radar_tiles": {"template": "https://example.com/tiles/{z}/{x}/{y}.png"}, "alerts": True}

@router.get("/alerts")
async def alerts(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency), limit: int = 200):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("weather_alerts").list(tenant_id=current.tenant_id, limit=limit, offset=0)

@router.get("/aviation")
async def aviation(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency), limit: int = 200):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("aviation_weather_reports").list(tenant_id=current.tenant_id, limit=limit, offset=0)

@router.post("/refresh", dependencies=[Depends(require_role("admin","founder"))])
async def refresh(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    # record refresh request for worker
    return await svc.create(table="weather_tiles_cache", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"action":"refresh","payload":payload}, correlation_id=getattr(request.state,"correlation_id",None))

