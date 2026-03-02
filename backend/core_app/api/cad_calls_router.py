from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/cad", tags=["CAD"])

_ALS_COMPLAINTS = {
    "cardiac arrest",
    "chest pain",
    "stroke",
    "difficulty breathing",
    "respiratory distress",
    "altered mental status",
    "seizure",
    "anaphylaxis",
    "overdose",
    "major trauma",
    "unconscious",
    "unresponsive",
}
_CCT_COMPLAINTS = {
    "ventilator dependent",
    "critical care transfer",
    "post cardiac arrest",
    "aortic dissection",
    "intracranial hemorrhage",
}
_HIGH_RISK_MECHANISMS = {
    "mvc high speed",
    "fall > 20 feet",
    "penetrating torso",
    "explosion",
    "electrocution",
    "drowning",
    "hanging",
}


def _compute_acuity(payload: dict[str, Any]) -> dict[str, Any]:
    complaint = str(payload.get("chief_complaint") or "").strip().lower()
    priority = str(payload.get("priority") or "").strip().lower()
    age = payload.get("age_years")
    distance = payload.get("distance_miles")
    mechanism = str(payload.get("mechanism") or "").strip().lower()
    cardiac_arrest = bool(payload.get("cardiac_arrest"))
    respiratory_distress = bool(payload.get("respiratory_distress"))
    altered_mental_status = bool(payload.get("altered_mental_status"))

    triggered_rules: list[str] = []
    risk_flags: list[str] = []
    suggested_questions: list[str] = []

    level = "BLS"
    score = 0

    if cardiac_arrest:
        level = "ALS"
        score += 40
        triggered_rules.append("R01:cardiac_arrest_immediate_als")
        risk_flags.append("CARDIAC_ARREST")
        suggested_questions.append("Is CPR in progress?")
        suggested_questions.append("Is an AED available on scene?")

    if respiratory_distress:
        score += 20
        triggered_rules.append("R02:respiratory_distress_als_indicator")
        risk_flags.append("RESPIRATORY_DISTRESS")
        suggested_questions.append("Is the patient able to speak in full sentences?")

    if altered_mental_status:
        score += 15
        triggered_rules.append("R03:altered_mental_status_als_indicator")
        risk_flags.append("ALTERED_MENTAL_STATUS")
        suggested_questions.append("What is the patient's GCS?")

    for cct_term in _CCT_COMPLAINTS:
        if cct_term in complaint:
            level = "CCT"
            score += 35
            triggered_rules.append(f"R04:cct_complaint:{cct_term.replace(' ', '_')}")
            break
    else:
        for als_term in _ALS_COMPLAINTS:
            if als_term in complaint:
                if level != "CCT":
                    level = "ALS"
                score += 25
                triggered_rules.append(f"R05:als_complaint:{als_term.replace(' ', '_')}")
                break

    for mech in _HIGH_RISK_MECHANISMS:
        if mech in mechanism:
            if level == "BLS":
                level = "ALS"
            score += 15
            triggered_rules.append(f"R06:high_risk_mechanism:{mech.replace(' ', '_')}")
            risk_flags.append("HIGH_RISK_MECHANISM")
            break

    if priority in ("p1", "priority 1", "echo", "delta"):
        if level == "BLS":
            level = "ALS"
        score += 10
        triggered_rules.append(f"R07:high_priority_dispatch:{priority}")

    if age is not None:
        try:
            age_val = float(age)
            if age_val < 2:
                score += 10
                triggered_rules.append("R08:pediatric_age_lt_2")
                risk_flags.append("PEDIATRIC_HIGH_RISK")
                suggested_questions.append("What is the infant's weight?")
            elif age_val > 80:
                score += 5
                triggered_rules.append("R09:geriatric_age_gt_80")
                risk_flags.append("GERIATRIC")
        except (TypeError, ValueError):
            pass

    if distance is not None:
        try:
            dist_val = float(distance)
            if dist_val > 30 and level == "BLS":
                level = "ALS"
                score += 5
                triggered_rules.append("R10:long_distance_als_upgrade")
        except (TypeError, ValueError):
            pass

    score = min(score, 100)
    if score >= 60:
        confidence = 0.95
    elif score >= 35:
        confidence = 0.85
    elif score >= 15:
        confidence = 0.75
    else:
        confidence = 0.65

    required_docs: list[str] = []
    if level in ("ALS", "CCT"):
        required_docs.append("pcr_als_section")
    if cardiac_arrest:
        required_docs.append("code_sheet")
    if level == "CCT":
        required_docs.append("cct_transfer_form")
        required_docs.append("receiving_physician_orders")

    return {
        "recommended_level": level,
        "confidence": confidence,
        "acuity_score": score,
        "triggered_rules": triggered_rules,
        "risk_flags": risk_flags,
        "required_docs": required_docs,
        "suggested_questions": suggested_questions,
    }


@router.post("/calls")
async def create_call(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="calls",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/calls/{call_id}/intake/answer")
async def intake_answer(
    call_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    payload = dict(payload)
    payload["call_id"] = str(call_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="call_intake_answers",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/calls/{call_id}/decision/compute")
async def compute_decision(
    call_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    acuity = _compute_acuity(payload)
    decision = {
        "call_id": str(call_id),
        "input": payload,
        "recommended_level": acuity["recommended_level"],
        "confidence": acuity["confidence"],
        "acuity_score": acuity["acuity_score"],
        "triggered_rules": acuity["triggered_rules"],
        "required_docs": acuity["required_docs"],
        "risk_flags": acuity["risk_flags"],
        "suggested_questions": acuity["suggested_questions"],
        "engine_version": "v1",
    }
    return await svc.create(
        table="dispatch_decisions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=decision,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/calls/{call_id}/decision/finalize")
async def finalize_decision(
    call_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if payload.get("override") and not payload.get("override_reason"):
        return {"error": "override_reason_required"}
    payload = dict(payload)
    payload["call_id"] = str(call_id)
    payload["finalized_by"] = str(current.user_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="dispatch_decisions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/calls/{call_id}/assign")
async def assign_unit(
    call_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    payload = dict(payload)
    payload["call_id"] = str(call_id)
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="crew_assignments",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/calls/{call_id}/status")
async def set_call_status(
    call_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    status = payload.get("status")
    expected_version = int(payload.get("expected_version", 0))
    svc = DominationService(db, get_event_publisher())
    updated = svc.repo("calls").update(
        tenant_id=current.tenant_id,
        record_id=call_id,
        expected_version=expected_version,
        patch={"status": status},
    )
    if updated is None:
        event = {"call_id": str(call_id), "status": status}
        return await svc.create(
            table="schedule_audit_events",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data=event,
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    return updated


@router.get("/ops/board")
async def ops_board(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
    limit: int = 200,
):
    svc = DominationService(db, get_event_publisher())
    return {
        "calls": svc.repo("calls").list(tenant_id=current.tenant_id, limit=limit, offset=0),
        "unit_status_events": svc.repo("unit_status_events").list(
            tenant_id=current.tenant_id, limit=limit, offset=0
        ),
        "unit_locations": svc.repo("unit_locations").list(
            tenant_id=current.tenant_id, limit=limit, offset=0
        ),
        "weather_alerts": svc.repo("weather_alerts").list(
            tenant_id=current.tenant_id, limit=limit, offset=0
        ),
        "fleet_alerts": svc.repo("fleet_alerts").list(
            tenant_id=current.tenant_id, limit=limit, offset=0
        ),
        "crew_pages": svc.repo("pages").list(tenant_id=current.tenant_id, limit=limit, offset=0),
    }
