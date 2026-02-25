from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/fleet", tags=['Fleet'])


@router.get("/dashboard")
async def dashboard(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return {"alerts": svc.repo("fleet_alerts").list(tenant_id=current.tenant_id, limit=200, offset=0), "maintenance": svc.repo("maintenance_items").list(tenant_id=current.tenant_id, limit=200, offset=0)}

@router.post("/maintenance")
async def maintenance(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="maintenance_items", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/inspections/checklists")
async def checklists(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="inspection_checklists", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/alerts/{alert_id}/ack")
async def ack(alert_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("fleet_alerts").update(tenant_id=current.tenant_id, record_id=alert_id, expected_version=int(payload.get("expected_version",0)), patch={"acknowledged": True})
    return rec or {"error":"not_found"}

