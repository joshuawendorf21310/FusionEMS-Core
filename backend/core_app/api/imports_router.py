from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/imports", tags=['Imports'])


@router.post("/create")
async def create_batch(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="import_batches", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/{batch_id}/upload-url")
async def upload(batch_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user)):
    return {"batch_id": str(batch_id), "method":"PUT", "url": payload.get("url") or ""}

@router.post("/{batch_id}/map")
async def map_batch(batch_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"batch_id": str(batch_id), "mapping": payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="import_mappings", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/{batch_id}/run")
async def run_batch(batch_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="import_errors", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"batch_id": str(batch_id), "status":"queued"}, correlation_id=getattr(request.state,"correlation_id",None))

