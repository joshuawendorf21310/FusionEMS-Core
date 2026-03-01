from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/cases", tags=["Cases"])

ALLOWED_ROLES = {"founder", "agency_admin", "admin", "dispatcher", "ems"}

VALID_STATUSES = {
    "intake",
    "queued",
    "dispatched",
    "enroute",
    "onscene",
    "transporting",
    "at_destination",
    "complete",
    "cancelled",
    "billed",
}

VALID_MODES = {"ground", "rotor", "fixed_wing"}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/")
async def create_case(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    mode = payload.get("transport_mode", "ground")
    if mode not in VALID_MODES:
        raise HTTPException(
            status_code=422, detail=f"transport_mode must be one of {sorted(VALID_MODES)}"
        )
    correlation_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)
    case = await svc.create(
        table="cases",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "transport_mode": mode,
            "status": "intake",
            "priority": payload.get("priority", "routine"),
            "transport_request_id": payload.get("transport_request_id"),
            "cad_call_id": payload.get("cad_call_id"),
            "crew_assignment_id": None,
            "epcr_chart_id": None,
            "billing_snapshot_id": None,
            "facility_id": payload.get("facility_id"),
            "patient_name": payload.get("patient_name", ""),
            "origin_address": payload.get("origin_address", ""),
            "destination_address": payload.get("destination_address", ""),
            "cms_gate_passed": False,
            "cms_gate_score": None,
            "cms_gate_result": None,
            "opened_at": datetime.now(UTC).isoformat(),
            "closed_at": None,
            "timeline": [],
            "tags": payload.get("tags", []),
        },
        correlation_id=correlation_id,
    )
    return case


@router.get("/")
async def list_cases(
    status: str | None = None,
    transport_mode: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    cases = svc.repo("cases").list(tenant_id=current.tenant_id, limit=min(limit, 200))
    if status:
        cases = [c for c in cases if (c.get("data") or {}).get("status") == status]
    if transport_mode:
        cases = [c for c in cases if (c.get("data") or {}).get("transport_mode") == transport_mode]
    return cases


@router.get("/{case_id}")
async def get_case(
    case_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    case = svc.repo("cases").get(tenant_id=current.tenant_id, record_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}/status")
async def transition_status(
    case_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    new_status = payload.get("status", "")
    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"Invalid status. Must be one of {sorted(VALID_STATUSES)}"
        )
    svc = _svc(db)
    case = svc.repo("cases").get(tenant_id=current.tenant_id, record_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    data = dict(case.get("data") or {})
    timeline = list(data.get("timeline") or [])
    timeline.append(
        {
            "status": new_status,
            "at": datetime.now(UTC).isoformat(),
            "by": str(current.user_id),
            "note": payload.get("note"),
        }
    )
    data["status"] = new_status
    data["timeline"] = timeline
    if new_status in ("complete", "cancelled", "billed"):
        data["closed_at"] = datetime.now(UTC).isoformat()
    updated = await svc.update(
        table="cases",
        tenant_id=current.tenant_id,
        record_id=case_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=case.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return updated


@router.patch("/{case_id}/link")
async def link_entity(
    case_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    case = svc.repo("cases").get(tenant_id=current.tenant_id, record_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    data = dict(case.get("data") or {})
    linkable = {
        "transport_request_id",
        "cad_call_id",
        "crew_assignment_id",
        "epcr_chart_id",
        "billing_snapshot_id",
        "facility_id",
    }
    for k, v in payload.items():
        if k in linkable:
            data[k] = v
    updated = await svc.update(
        table="cases",
        tenant_id=current.tenant_id,
        record_id=case_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=case.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return updated


@router.get("/{case_id}/timeline")
async def get_timeline(
    case_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    case = svc.repo("cases").get(tenant_id=current.tenant_id, record_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case_id": str(case_id), "timeline": (case.get("data") or {}).get("timeline", [])}
