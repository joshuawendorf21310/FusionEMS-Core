from __future__ import annotations

import uuid
from typing import Any

import boto3
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
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
    settings = get_settings()
    filename = str(payload.get("filename") or f"{request_id}.bin")
    s3_key = f"transportlink/{current.tenant_id}/{request_id}/{filename}"
    presigned_url = ""
    if settings.s3_bucket_docs:
        s3 = boto3.client("s3")
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.s3_bucket_docs, "Key": s3_key, "ContentType": payload.get("content_type") or "application/octet-stream"},
            ExpiresIn=900,
        )
    return {"request_id": str(request_id), "upload": {"method": "PUT", "url": presigned_url, "key": s3_key, "expires_in": 900}}

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
    svc = DominationService(db, get_event_publisher())
    return svc.repo("facility_requests").list(tenant_id=current.tenant_id, limit=500, offset=0)
