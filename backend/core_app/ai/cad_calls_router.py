from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/cad", tags=['CAD'])


@router.post("/calls")
async def create_call(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    # store as calls record; caller provides fields in payload
    return await svc.create(table="calls", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state, "correlation_id", None))

@router.post("/calls/{call_id}/intake/answer")
async def intake_answer(call_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    payload = dict(payload)
    payload["call_id"] = str(call_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="call_intake_answers", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state, "correlation_id", None))

@router.post("/calls/{call_id}/decision/compute")
async def compute_decision(call_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # deterministic rule engine placeholder: saves input + echo output; AI augmentation occurs in ai module
    svc = DominationService(db, get_event_publisher())
    decision = {
        "call_id": str(call_id),
        "input": payload,
        "recommended_level": payload.get("requested_level") or "BLS",
        "confidence": 0.75,
        "triggered_rules": [],
        "required_docs": [],
        "risk_flags": [],
        "suggested_questions": [],
        "engine_version": "v1"
    }
    return await svc.create(table="dispatch_decisions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=decision, correlation_id=getattr(request.state, "correlation_id", None))

@router.post("/calls/{call_id}/decision/finalize")
async def finalize_decision(call_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # finalize by writing another dispatch_decisions record with override_reason if any
    if payload.get("override") and not payload.get("override_reason"):
        return {"error": "override_reason_required"}
    payload = dict(payload)
    payload["call_id"] = str(call_id)
    payload["finalized_by"] = str(current.user_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="dispatch_decisions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state, "correlation_id", None))

@router.post("/calls/{call_id}/assign")
async def assign_unit(call_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # writes crew_assignments record
    payload = dict(payload)
    payload["call_id"] = str(call_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="crew_assignments", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state, "correlation_id", None))

@router.post("/calls/{call_id}/status")
async def set_call_status(call_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # create unit_status_events or update call record
    status = payload.get("status")
    expected_version = int(payload.get("expected_version", 0))
    svc = DominationService(db, get_event_publisher())
    # patch call record if exists; otherwise store event
    updated = svc.repo("calls").update(tenant_id=current.tenant_id, record_id=call_id, expected_version=expected_version, patch={"status": status})
    if updated is None:
        event = {"call_id": str(call_id), "status": status}
        return await svc.create(table="schedule_audit_events", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=event, correlation_id=getattr(request.state, "correlation_id", None))
    return updated

@router.get("/ops/board")
async def ops_board(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency), limit: int = 200):
    svc = DominationService(db, get_event_publisher())
    return {
        "calls": svc.repo("calls").list(tenant_id=current.tenant_id, limit=limit, offset=0),
        "unit_status_events": svc.repo("unit_status_events").list(tenant_id=current.tenant_id, limit=limit, offset=0),
        "unit_locations": svc.repo("unit_locations").list(tenant_id=current.tenant_id, limit=limit, offset=0),
        "weather_alerts": svc.repo("weather_alerts").list(tenant_id=current.tenant_id, limit=limit, offset=0),
        "fleet_alerts": svc.repo("fleet_alerts").list(tenant_id=current.tenant_id, limit=limit, offset=0),
        "crew_pages": svc.repo("pages").list(tenant_id=current.tenant_id, limit=limit, offset=0),
    }

