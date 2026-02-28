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


@router.post("/reports/{report_id}/statements")
async def create_statement(report_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"report_id": str(report_id), **payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="fire_statements", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/reports/{report_id}/statements")
async def list_statements(report_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return svc.repo("fire_statements").list(tenant_id=current.tenant_id, limit=200, offset=0)

