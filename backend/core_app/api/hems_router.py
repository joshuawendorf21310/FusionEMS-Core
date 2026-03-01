from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.epcr.chart_model import Chart
from core_app.epcr.completeness_engine import CompletenessEngine
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
            "accepted_at": datetime.now(UTC).isoformat(),
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
            "briefed_at": datetime.now(UTC).isoformat(),
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
            "set_at": datetime.now(UTC).isoformat(),
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
            "audited_at": datetime.now(UTC).isoformat(),
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


@router.post("/missions/{mission_id}/acknowledge")
async def acknowledge_mission(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    decision = payload.get("decision", "accept")
    if decision not in ("accept", "decline"):
        raise HTTPException(status_code=422, detail="decision must be 'accept' or 'decline'")
    svc = _svc(db)
    row = await svc.create(
        table="hems_mission_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "event_type": "pilot_acknowledge",
            "pilot_user_id": str(current.user_id),
            "decision": decision,
            "decline_reason": payload.get("decline_reason"),
            "acknowledged_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.post("/missions/{mission_id}/wheels-up")
async def record_wheels_up(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    wheels_up_time = payload.get("wheels_up_time") or datetime.now(UTC).isoformat()
    row = await svc.create(
        table="hems_mission_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "event_type": "wheels_up",
            "pilot_user_id": str(current.user_id),
            "aircraft_id": payload.get("aircraft_id"),
            "wheels_up_time": wheels_up_time,
            "crew": payload.get("crew", []),
            "fuel_on_board_lbs": payload.get("fuel_on_board_lbs"),
            "destination": payload.get("destination"),
            "lz_coords": payload.get("lz_coords"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.post("/missions/{mission_id}/wheels-down")
async def record_wheels_down(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    wheels_down_time = payload.get("wheels_down_time") or datetime.now(UTC).isoformat()
    row = await svc.create(
        table="hems_mission_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "event_type": "wheels_down",
            "pilot_user_id": str(current.user_id),
            "wheels_down_time": wheels_down_time,
            "destination_actual": payload.get("destination_actual"),
            "patient_status": payload.get("patient_status"),
            "fuel_on_board_lbs": payload.get("fuel_on_board_lbs"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.post("/missions/{mission_id}/complete")
async def complete_mission(
    mission_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    completed_at = datetime.now(UTC).isoformat()
    row = await svc.create(
        table="hems_mission_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "event_type": "mission_complete",
            "pilot_user_id": str(current.user_id),
            "completed_at": completed_at,
            "outcome": payload.get("outcome"),
            "transport_minutes": payload.get("transport_minutes"),
            "epcr_opened": False,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    billing_row = await svc.create(
        table="billing_cases",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "mission_id": str(mission_id),
            "service_type": "HEMS",
            "status": "pending_epcr",
            "created_at": completed_at,
            "transport_minutes": payload.get("transport_minutes"),
            "outcome": payload.get("outcome"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    chart_id = str(uuid.uuid4())
    chart = Chart(
        chart_id=chart_id,
        tenant_id=str(current.tenant_id),
        chart_mode="hems",
        created_by=str(current.user_id),
        last_modified_by=str(current.user_id),
    )
    chart_dict = chart.to_dict()
    chart_dict["mission_id"] = str(mission_id)
    chart_dict["billing_case_id"] = str(billing_row["id"])
    chart_dict["wheels_up_time"] = payload.get("wheels_up_time")
    chart_dict["wheels_down_time"] = payload.get("wheels_down_time")
    score_result = CompletenessEngine().score_chart(chart_dict, "hems")
    chart_dict["completeness_score"] = score_result["score"]
    chart_dict["completeness_issues"] = [m["label"] for m in score_result["missing"]]
    epcr_row = await svc.create(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=chart_dict,
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    return {
        "mission_event_id": row["id"],
        "billing_case_id": billing_row["id"],
        "epcr_chart_id": epcr_row["id"],
        "status": "completed",
        "epcr_required": True,
    }


@router.get("/missions/stream")
async def mission_stream(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    from fastapi.responses import StreamingResponse

    async def event_generator():
        svc = _svc(db)
        last_event_ids: dict[str, str] = {}
        while True:
            if await request.is_disconnected():
                break

            tables = ["hems_mission_events", "aircraft_readiness_events", "hems_weather_briefs"]
            for table in tables:
                rows = svc.repo(table).list(tenant_id=current.tenant_id, limit=10, offset=0)
                for row in sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)[:5]:
                    row_id = str(row.get("id", ""))
                    if last_event_ids.get(table) != row_id:
                        last_event_ids[table] = row_id
                        event_type = (row.get("data") or {}).get("event_type", table.replace("_", "-"))
                        yield f"event: {event_type}\ndata: {json.dumps(row)}\n\n"

            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/weather/fetch")
async def fetch_live_weather(
    icao: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Fetch live METAR + TAF from aviationweather.gov (free, no auth required)."""
    import httpx

    _check(current)
    icao = icao.upper().strip()
    if not icao or len(icao) < 3 or len(icao) > 5:
        raise HTTPException(status_code=422, detail="icao must be 3-5 characters")

    base = "https://aviationweather.gov/api/data"
    results: dict[str, Any] = {"icao": icao, "metar": None, "taf": None, "source": "aviationweather.gov"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            metar_r = await client.get(f"{base}/metar", params={"ids": icao, "format": "json"})
            if metar_r.status_code == 200:
                data = metar_r.json()
                if isinstance(data, list) and data:
                    results["metar"] = data[0]
        except httpx.HTTPError:
            results["metar_error"] = "fetch_failed"

        try:
            taf_r = await client.get(f"{base}/taf", params={"ids": icao, "format": "json"})
            if taf_r.status_code == 200:
                data = taf_r.json()
                if isinstance(data, list) and data:
                    results["taf"] = data[0]
        except httpx.HTTPError:
            results["taf_error"] = "fetch_failed"

    if not results["metar"] and not results["taf"]:
        raise HTTPException(
            status_code=404,
            detail=f"No weather data found for ICAO {icao}. Verify station identifier.",
        )

    svc = _svc(db)
    await svc.create(
        table="aviation_weather_reports",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "icao": icao,
            "metar": results.get("metar"),
            "taf": results.get("taf"),
            "fetched_at": datetime.now(UTC).isoformat(),
            "source": "aviationweather.gov",
        },
        correlation_id=None,
    )

    return results
