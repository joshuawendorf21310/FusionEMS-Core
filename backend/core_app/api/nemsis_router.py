from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/nemsis", tags=["NEMSIS"])

@router.post("/validate")
async def validate(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # Stores validation result; full XSD/Schematron executed by compliance module/harness in this build
    svc = DominationService(db, get_event_publisher())
    result = {"status": "queued", "input": payload}
    return await svc.create(table="nemsis_validation_results", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=result, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/exports")
async def create_export(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    job = {"status":"queued","range":payload.get("range"),"agency":payload.get("agency")}
    return await svc.create(table="nemsis_export_jobs", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=job, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/exports/{job_id}")
async def get_export(job_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("nemsis_export_jobs").get(tenant_id=current.tenant_id, record_id=job_id)
    return rec or {"error":"not_found"}
