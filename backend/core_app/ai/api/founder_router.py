from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/founder", tags=['Founder'])


@router.get("/tenants", dependencies=[Depends(require_role("founder","admin"))])
async def tenants(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # return minimal tenant health/compliance summary for current tenant only in monolith
    svc = DominationService(db, get_event_publisher())
    scores = svc.repo("governance_scores").list(tenant_id=current.tenant_id, limit=50, offset=0)
    return [{"tenant_id": str(current.tenant_id), "governance_scores": scores}]

@router.get("/tenants/{tenant_id}/billing", dependencies=[Depends(require_role("founder","admin","billing"))])
async def tenant_billing(tenant_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return {"billing_jobs": svc.repo("billing_jobs").list(tenant_id=current.tenant_id, limit=200, offset=0), "claims": svc.repo("claims").list(tenant_id=current.tenant_id, limit=200, offset=0)}

@router.get("/tenants/{tenant_id}/compliance", dependencies=[Depends(require_role("founder","admin"))])
async def tenant_compliance(tenant_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return {"nemsis": svc.repo("nemsis_validation_results").list(tenant_id=current.tenant_id, limit=50, offset=0),
            "neris": svc.repo("neris_validation_results").list(tenant_id=current.tenant_id, limit=50, offset=0),
            "scores": svc.repo("governance_scores").list(tenant_id=current.tenant_id, limit=50, offset=0)}

@router.post("/support/impersonate/start", dependencies=[Depends(require_role("founder"))])
async def impersonate(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # record support_session; real impersonation requires separate auth layer
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="support_sessions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"type":"impersonate", **payload}, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/support/session/start", dependencies=[Depends(require_role("founder"))])
async def support_session(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="support_sessions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"type":"remote_support", **payload}, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/ai/chat", dependencies=[Depends(require_role("founder","admin"))])
async def ai_chat(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # store ai_run record; actual provider invoked only if keys configured
    svc = DominationService(db, get_event_publisher())
    run = {"prompt": payload.get("message"), "model": payload.get("model","gpt-4.1"), "status":"queued"}
    return await svc.create(table="ai_runs", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=run, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/docs/generate", dependencies=[Depends(require_role("founder","admin"))])
async def docs(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user)):
    # placeholder contract: actual generation handled by backend document generator module
    return {"status":"accepted","kind":payload.get("kind"),"name":payload.get("name")}

