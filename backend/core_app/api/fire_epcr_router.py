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


@router.post("/reports")
async def create_report(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="fire_reports", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.patch("/reports/{report_id}")
async def autosave(report_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    expected_version = int(payload.get("expected_version",0))
    patch = dict(payload)
    patch.pop("expected_version", None)
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("fire_reports").update(tenant_id=current.tenant_id, record_id=report_id, expected_version=expected_version, patch=patch)
    return rec or {"error":"conflict_or_not_found"}

@router.post("/reports/{report_id}/lock")
async def lock(report_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("fire_reports").update(tenant_id=current.tenant_id, record_id=report_id, expected_version=int(payload.get("expected_version",0)), patch={"locked": True})
    return rec or {"error":"conflict_or_not_found"}

