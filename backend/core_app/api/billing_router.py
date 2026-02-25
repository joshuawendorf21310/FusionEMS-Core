from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/billing", tags=['Billing'])


@router.post("/cases/{case_id}/validate")
async def validate(case_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # perform minimal validation: missing docs list from payload; store billing_job result
    svc = DominationService(db, get_event_publisher())
    result = {"case_id": str(case_id), "missing_docs": payload.get("missing_docs", []), "risk": 0.2}
    return await svc.create(table="billing_jobs", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"type":"validate","result":result}, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/cases/{case_id}/submit-officeally")
async def submit(case_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # create EDI artifact record (file generation handled by worker/integration)
    svc = DominationService(db, get_event_publisher())
    artifact = {"case_id": str(case_id), "kind":"837", "status":"queued"}
    return await svc.create(table="edi_artifacts", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=artifact, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/eras/import")
async def import_era(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="eras", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/claims/{claim_id}/appeal/generate")
async def appeal(claim_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="appeals", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"claim_id": str(claim_id), **payload}, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/payment/link")
async def payment_link(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # store link record with stripe session id only
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="patient_payment_links", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"stripe_session_id": payload.get("stripe_session_id"), "phone": payload.get("phone")}, correlation_id=getattr(request.state,"correlation_id",None))

