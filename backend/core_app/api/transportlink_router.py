from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/transportlink", tags=['TransportLink'])


@router.post("/requests")
async def create_request(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="facility_requests", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/requests/{request_id}/upload-url")
async def upload_url(request_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # placeholder presign: return structured response; actual presign done in documents module when s3 configured
    return {"request_id": str(request_id), "upload": {"method": "PUT", "url": payload.get("url") or ""}}

@router.post("/requests/{request_id}/submit")
async def submit(request_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    patch = {"status": "submitted"}
    rec = svc.repo("facility_requests").update(tenant_id=current.tenant_id, record_id=request_id, expected_version=int(payload.get("expected_version",0)), patch=patch)
    return rec or {"error":"not_found"}

@router.get("/requests/{request_id}/status")
async def status(request_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("facility_requests").get(tenant_id=current.tenant_id, record_id=request_id)
    return rec or {"error":"not_found"}

@router.get("/facilities/{facility_id}/schedule")
async def facility_schedule(facility_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # return requests for facility
    svc = DominationService(db, get_event_publisher())
    return svc.repo("facility_requests").list(tenant_id=current.tenant_id, limit=500, offset=0)

