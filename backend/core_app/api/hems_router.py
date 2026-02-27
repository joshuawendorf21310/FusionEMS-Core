from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/hems", tags=["HEMS"])

ALLOWED_ROLES = {"founder", "agency_admin", "admin", "dispatcher", "pilot", "ems"}

AIRCRAFT_READINESS_STATES = {"ready", "limited", "no_go", "maintenance_hold", "out_of_service"}

ACCEPTANCE_CHECKLIST_ITEMS = [
    {"id": "wx_reviewed", "label": "Weather brief reviewed"},
    {"id": "minima_met", "label": "Weather minima met for flight type"},
    {"id": "aircraft_preflight", "label": "Aircraft preflight completed"},
    {"id": "fuel_sufficient", "label": "Fuel sufficient for mission + reserve"},
    {"id": "crew_rest", "label": "Crew rest requirements met (8hr rule)"},
    {"id": "crew_briefed", "label": "Crew briefed on mission and LZ"},
    {"id": "comms_check", "label": "Comms check with dispatch completed"},
    {"id": "lz_info_received", "label": "LZ information received and assessed"},
    {"id": "medical_crew_ready", "label": "Medical crew ready and equipment checked"},
    {"id": "no_safety_concerns", "label": "No unresolved safety concerns"},
]

RISK_FACTORS = [
    {"id": "night_ops", "label": "Night operations", "weight": 15},
    {"id": "mountainous_terrain", "label": "Mountainous/complex terrain", "weight": 15},
    {"id": "marginal_wx", "label": "Marginal weather (near minima)", "weight": 20},
    {"id": "unfamiliar_lz", "label": "Unfamiliar landing zone", "weight": 10},
    {"id": "single_pilot", "label": "Single pilot operations", "weight": 10},
    {"id": "critical_patient", "label": "Critical patient (ALS/HEMS required)", "weight": 5},
    {"id": "long_transport", "label": "Long transport distance (>60 min)", "weight": 10},
    {"id": "comms_degraded", "label": "Degraded communications", "weight": 15},
]


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/checklist-template")
async def checklist_template(current: CurrentUser = Depends(get_current_user)):
    _check(current)
    return {"items": ACCEPTANCE_CHECKLIST_ITEMS, "risk_factors": RISK_FACTORS}


@router.post("/missions/{mission_id}/acceptance")
async def submit_acceptance(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    checklist = payload.get("checklist", {})
    risk_flags = payload.get("risk_flags", [])
    all_required = {item["id"] for item in ACCEPTANCE_CHECKLIST_ITEMS}
    missing = [item_id for item_id in all_required if not checklist.get(item_id)]
    if missing and not payload.get("force_accept"):
        raise HTTPException(
            status_code=422,
            detail={"message": "Acceptance checklist incomplete", "missing_items": missing},
        )
    risk_score = sum(
        f["weight"] for f in RISK_FACTORS if f["id"] in risk_flags
    )
    risk_level = "low" if risk_score < 20 else "medium" if risk_score < 45 else "high"
    correlation_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)
    record = await svc.create(
        table="hems_acceptance_records",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "pilot_user_id": str(current.user_id),
            "checklist": checklist,
            "missing_items": missing,
            "risk_flags": risk_flags,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "force_accepted": bool(payload.get("force_accept")),
            "force_reason": payload.get("force_reason"),
            "accepted": True,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "wx_ceiling_ft": payload.get("wx_ceiling_ft"),
            "wx_visibility_sm": payload.get("wx_visibility_sm"),
            "wx_wind_kt": payload.get("wx_wind_kt"),
            "wx_source": payload.get("wx_source", "AWOS"),
            "notes": payload.get("notes"),
        },
        correlation_id=correlation_id,
    )
    return record


@router.post("/missions/{mission_id}/weather-brief")
async def submit_weather_brief(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="hems_weather_briefs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "pilot_user_id": str(current.user_id),
            "briefed_at": datetime.now(timezone.utc).isoformat(),
            "source": payload.get("source", "1800wxbrief"),
            "ceiling_ft": payload.get("ceiling_ft"),
            "visibility_sm": payload.get("visibility_sm"),
            "wind_direction": payload.get("wind_direction"),
            "wind_speed_kt": payload.get("wind_speed_kt"),
            "gusts_kt": payload.get("gusts_kt"),
            "precip": payload.get("precip", False),
            "icing": payload.get("icing", False),
            "turbulence": payload.get("turbulence", "none"),
            "minima_profile": payload.get("minima_profile", "day_vfr"),
            "go_no_go": payload.get("go_no_go", "go"),
            "raw_brief": payload.get("raw_brief"),
        },
        correlation_id=correlation_id,
    )


@router.get("/missions/{mission_id}/acceptance")
async def get_acceptance(
    mission_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    records = svc.repo("hems_acceptance_records").list(tenant_id=current.tenant_id, limit=50)
    matching = [r for r in records if (r.get("data") or {}).get("mission_id") == str(mission_id)]
    return matching


@router.post("/aircraft/{aircraft_id}/readiness")
async def set_aircraft_readiness(
    aircraft_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    state = payload.get("state", "ready")
    if state not in AIRCRAFT_READINESS_STATES:
        raise HTTPException(status_code=422, detail=f"state must be one of {sorted(AIRCRAFT_READINESS_STATES)}")
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="aircraft_readiness_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "aircraft_id": str(aircraft_id),
            "state": state,
            "reason": payload.get("reason"),
            "maintenance_hold": payload.get("maintenance_hold", False),
            "hold_until": payload.get("hold_until"),
            "set_by": str(current.user_id),
            "set_at": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=correlation_id,
    )


@router.get("/aircraft/{aircraft_id}/readiness")
async def get_aircraft_readiness(
    aircraft_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    events = svc.repo("aircraft_readiness_events").list(tenant_id=current.tenant_id, limit=100)
    matching = [e for e in events if (e.get("data") or {}).get("aircraft_id") == str(aircraft_id)]
    if not matching:
        return {"aircraft_id": str(aircraft_id), "state": "unknown", "history": []}
    latest = sorted(matching, key=lambda x: x.get("created_at", ""), reverse=True)[0]
    return {
        "aircraft_id": str(aircraft_id),
        "state": (latest.get("data") or {}).get("state", "unknown"),
        "latest_event": latest,
        "history": matching[:20],
    }


@router.post("/missions/{mission_id}/risk-audit")
async def submit_risk_audit(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    risk_flags = payload.get("risk_flags", [])
    risk_score = sum(f["weight"] for f in RISK_FACTORS if f["id"] in risk_flags)
    risk_level = "low" if risk_score < 20 else "medium" if risk_score < 45 else "high"
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="hems_risk_audits",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "pilot_user_id": str(current.user_id),
            "risk_flags": risk_flags,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors_snapshot": RISK_FACTORS,
            "narrative": payload.get("narrative"),
            "audited_at": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=correlation_id,
    )


@router.get("/missions/{mission_id}/safety-timeline")
async def safety_timeline(
    mission_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    mid = str(mission_id)
    def fetch(table: str) -> list[dict]:
        rows = svc.repo(table).list(tenant_id=current.tenant_id, limit=50)
        return [r for r in rows if (r.get("data") or {}).get("mission_id") == mid]
    return {
        "mission_id": mid,
        "acceptance": fetch("hems_acceptance_records"),
        "weather_briefs": fetch("hems_weather_briefs"),
        "risk_audits": fetch("hems_risk_audits"),
    }
