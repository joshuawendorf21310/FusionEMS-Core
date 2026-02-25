from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.scheduling.engine import SchedulingEngine

router = APIRouter(prefix="/api/v1/scheduling", tags=['Scheduling'])


@router.post("/shifts/templates")
async def create_shift_template(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="shifts", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/shifts/instances/generate")
async def generate_instances(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    # simplistic generator: create one shift_instance per provided date in payload["dates"]
    svc = DominationService(db, get_event_publisher())
    created = []
    for d in payload.get("dates", []):
        inst = dict(payload)
        inst["date"] = d
        created.append(await svc.create(table="shift_instances", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=inst, correlation_id=getattr(request.state,"correlation_id",None)))
    return created

@router.post("/availability")
async def availability(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = dict(payload)
    data["user_id"] = str(current.user_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="availability_blocks", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/timeoff/request")
async def timeoff(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="time_off_requests", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/bid-cycles")
async def bid_cycles(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="bid_cycles", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/bids")
async def bids(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="shift_bids", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/coverage/dashboard")
async def coverage_dashboard(request: Request, hours: int = 24, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    require_role(current, ["founder","admin","dispatcher"])
    engine = SchedulingEngine(db, tenant_id=current.tenant_id)
    result = engine.coverage_dashboard(hours=hours)
    # Publish a snapshot event (lightweight)
    pub = get_event_publisher()
    pub.publish(
        topic=f"tenant.{current.tenant_id}.scheduling.coverage.snapshot",
        tenant_id=current.tenant_id,
        entity_type="scheduling",
        entity_id=str(current.tenant_id),
        event_type="COVERAGE_SNAPSHOT",
        payload={"hours": hours, "violations": result.get("violations", [])},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result

@router.post("/rotations")
async def rotations(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="on_call_rotations", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/credentials")
async def credentials(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="credentials", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.get("/credentials/expiring")
async def credentials_expiring(within_days: int = 30, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    require_role(current, ["founder","admin","dispatcher"])
    engine = SchedulingEngine(db, tenant_id=current.tenant_id)
    return {"within_days": within_days, "expiring": engine.list_expiring_credentials(within_days=within_days)}



@router.post("/scheduling/escalations/run")
async def run_escalations(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    require_role(current, ["founder","admin","dispatcher"])
    from core_app.scheduling.escalation import run_coverage_escalations
    res = run_coverage_escalations(db=db, tenant_id=current.tenant_id, within_hours=int(payload.get("within_hours", 4)))
    get_event_publisher().publish(
        topic=f"tenant.{current.tenant_id}.scheduling.escalations.run",
        tenant_id=current.tenant_id,
        entity_type="scheduling",
        entity_id=str(current.tenant_id),
        event_type="SCHEDULING_ESCALATIONS_RUN",
        payload=res,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return res
