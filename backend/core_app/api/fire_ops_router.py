from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/fire", tags=['Fire'])


@router.post("/incidents")
async def create_incident(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="fire_incidents", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/incidents/{incident_id}/assign")
async def assign(incident_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"incident_id": str(incident_id), **payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="fire_personnel_assignments", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/ops/board")
async def ops_board(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency), limit: int = 200):
    svc = DominationService(db, get_event_publisher())
    return {"fire_incidents": svc.repo("fire_incidents").list(tenant_id=current.tenant_id, limit=limit, offset=0)}

@router.post("/fire/preplans")
async def create_preplan(
    payload: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fire_preplans",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.get("/fire/preplans")
async def list_preplans(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("fire_preplans").list(tenant_id=current.tenant_id, limit=500)


@router.post("/fire/hydrants")
async def create_hydrant(
    payload: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fire_hydrants",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.get("/fire/hydrants")
async def list_hydrants(
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: float = 1.0,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    hydrants = svc.repo("fire_hydrants").list(tenant_id=current.tenant_id, limit=5000)
    if lat and lng:
        def _dist(h):
            hlat = h["data"].get("lat", 0)
            hlng = h["data"].get("lng", 0)
            dlat = (hlat - lat) * 69
            dlng = (hlng - lng) * 54.6
            return (dlat**2 + dlng**2) ** 0.5
        hydrants = [h for h in hydrants if _dist(h) <= radius_miles]
    return hydrants
