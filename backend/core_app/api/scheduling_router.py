from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.scheduling.ai_advisor import AISchedulingAdvisor
from core_app.scheduling.engine import SchedulingEngine
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

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


@router.post("/ai/draft")
async def ai_scheduling_draft(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    advisor = AISchedulingAdvisor(db, get_event_publisher(), current.tenant_id, current.user_id)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await advisor.generate_draft(
        horizon_hours=payload.get("horizon_hours", 48),
        correlation_id=correlation_id,
    )


@router.post("/ai/drafts/{draft_id}/approve")
async def approve_ai_draft(
    draft_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    advisor = AISchedulingAdvisor(db, get_event_publisher(), current.tenant_id, current.user_id)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        return await advisor.approve_draft(draft_id, correlation_id=correlation_id)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/ai/drafts")
async def list_ai_drafts(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    from core_app.services.domination_service import DominationService
    svc = DominationService(db, get_event_publisher())
    return svc.repo("ai_scheduling_drafts").list(tenant_id=current.tenant_id, limit=50)


@router.post("/what-if")
async def what_if_simulation(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    advisor = AISchedulingAdvisor(db, get_event_publisher(), current.tenant_id, current.user_id)
    return advisor.what_if_simulate(payload)


@router.get("/fatigue/report")
async def fatigue_report(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    from core_app.services.domination_service import DominationService
    svc = DominationService(db, get_event_publisher())
    assignments = svc.repo("crew_assignments").list(tenant_id=current.tenant_id, limit=1000)
    now = _dt.datetime.now(tz=_dt.UTC)
    crew_hours_7d: dict[str, float] = {}
    crew_hours_24h: dict[str, float] = {}
    for a in assignments:
        d = a.get("data") or {}
        crew_id = str(d.get("crew_member_id") or d.get("user_id") or "")
        if not crew_id:
            continue
        hours = float(d.get("hours", 12))
        shift_start_str = d.get("start_datetime") or a.get("created_at", "")
        try:
            shift_start = _dt.datetime.fromisoformat(shift_start_str.replace("Z", "+00:00"))
            delta_hours = (now - shift_start).total_seconds() / 3600
            if delta_hours <= 168:
                crew_hours_7d[crew_id] = crew_hours_7d.get(crew_id, 0) + hours
            if delta_hours <= 24:
                crew_hours_24h[crew_id] = crew_hours_24h.get(crew_id, 0) + hours
        except Exception:
            pass
    all_crew_ids = set(crew_hours_7d) | set(crew_hours_24h)
    report = []
    for cid in all_crew_ids:
        h7 = crew_hours_7d.get(cid, 0)
        h24 = crew_hours_24h.get(cid, 0)
        report.append({
            "crew_member_id": cid,
            "hours_last_24h": round(h24, 1),
            "hours_last_7d": round(h7, 1),
            "fatigue_risk_24h": h24 > 12,
            "fatigue_risk_7d": h7 > 48,
            "overtime_risk_7d": h7 > 40,
        })
    return {"report": sorted(report, key=lambda x: x["hours_last_7d"], reverse=True)}
