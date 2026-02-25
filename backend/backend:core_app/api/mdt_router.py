from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/mdt", tags=['MDT'])


@router.post("/units/{unit_id}/pair")
async def pair(unit_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = dict(payload)
    data["unit_id"] = str(unit_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="mdt_sessions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/units/{unit_id}/status")
async def status(unit_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"unit_id": str(unit_id), "status": payload.get("status")}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="unit_status_events", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/units/{unit_id}/gps")
async def gps(unit_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"unit_id": str(unit_id), "points": payload.get("points", [])}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="unit_locations", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/units/{unit_id}/obd")
async def obd(unit_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"unit_id": str(unit_id), "payload": payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="obd_readings", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/units/{unit_id}/camera/event")
async def camera_event(unit_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"unit_id": str(unit_id), "event": payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="camera_events", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/units/{unit_id}/active-call")
async def active_call(unit_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # return latest assignment for unit
    svc = DominationService(db, get_event_publisher())
    assigns = svc.repo("crew_assignments").list(tenant_id=current.tenant_id, limit=1, offset=0)
    return assigns[0] if assigns else None

