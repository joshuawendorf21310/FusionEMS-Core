from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/documents", tags=['Documents'])


@router.post("/upload-url")
async def upload_url(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # structured response; actual presign uses S3 integration when configured
    return {"method":"PUT","url":payload.get("url") or "", "headers":{}}

@router.post("/process")
async def process(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # create missing_document_task or extraction job
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="document_extractions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"document_id": payload.get("document_id"), "status":"queued"}, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/{document_id}")
async def get_doc(document_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("documents").get(tenant_id=current.tenant_id, record_id=document_id)
    return rec or {"error":"not_found"}

@router.post("/{document_id}/attach")
async def attach(document_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # create a task linking
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="missing_document_tasks", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"document_id": str(document_id), **payload}, correlation_id=getattr(request.state,"correlation_id",None))

