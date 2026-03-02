from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/cad", tags=["CAD"])


@router.post("/units", dependencies=[Depends(require_role("admin", "founder"))])
async def create_unit(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="units",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/units")
async def list_units(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 100,
    offset: int = 0,
):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("units").list(tenant_id=current.tenant_id, limit=limit, offset=offset)


@router.post("/units/{unit_id}/status")
async def set_unit_status(
    unit_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    event = {"unit_id": str(unit_id), "status": payload.get("status"), "ts": payload.get("ts")}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="unit_status_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=event,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
