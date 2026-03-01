from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.neris.exporter import NERISExporter
from core_app.neris.pack_manager import NERISPackManager
from core_app.neris.validator import NERISValidator
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/tenant/neris", tags=["NERIS Tenant"])

ALLOWED_ROLES = {"agency_admin", "founder", "admin"}

ONBOARDING_STEPS = [
    {"id": "1", "label": "Department Profile"},
    {"id": "2", "label": "Stations"},
    {"id": "3", "label": "Apparatus"},
    {"id": "4", "label": "Personnel"},
    {"id": "5", "label": "Incident Types & Value Sets"},
    {"id": "6", "label": "Entity Validation"},
    {"id": "7", "label": "Export Ready"},
]


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check_role(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


def _manager(db: Session, current: CurrentUser) -> NERISPackManager:
    return NERISPackManager(db, get_event_publisher(), current.tenant_id, current.user_id)


def _validator(db: Session, current: CurrentUser) -> NERISValidator:
    return NERISValidator(db, get_event_publisher(), current.tenant_id)


def _exporter(db: Session, current: CurrentUser) -> NERISExporter:
    return NERISExporter(db, get_event_publisher(), current.tenant_id, current.user_id)


def _get_onboarding(svc: DominationService, tenant_id: uuid.UUID) -> dict[str, Any] | None:
    records = svc.repo("neris_onboarding").list(tenant_id=tenant_id, limit=1)
    return records[0] if records else None


def _get_active_pack(svc: DominationService, tenant_id: uuid.UUID) -> dict[str, Any] | None:
    packs = svc.repo("neris_packs").list(tenant_id=tenant_id, limit=100)
    for p in packs:
        if (p.get("data") or {}).get("status") == "active":
            return p
    return None


@router.post("/onboarding/start")
async def onboarding_start(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)

    existing = _get_onboarding(svc, current.tenant_id)
    if existing:
        return {"onboarding": existing, "created": False}

    dept_id: str | None = payload.get("department_id")
    dept_name: str = payload.get("department_name", "")

    if not dept_id and dept_name:
        dept = await svc.create(
            table="fire_departments",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "name": dept_name,
                "state": payload.get("state", "WI"),
                "primary_contact_name": payload.get("primary_contact_name", ""),
                "primary_contact_email": payload.get("primary_contact_email", ""),
                "primary_contact_phone": payload.get("primary_contact_phone", ""),
            },
            correlation_id=correlation_id,
        )
        dept_id = str(dept["id"])

    step_status: dict[str, str] = {s["id"]: "pending" for s in ONBOARDING_STEPS}
    onboarding = await svc.create(
        table="neris_onboarding",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "department_id": dept_id,
            "current_step": "1",
            "step_status_json": step_status,
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
        },
        correlation_id=correlation_id,
    )
    return {"onboarding": onboarding, "created": True, "steps": ONBOARDING_STEPS}


@router.get("/onboarding/status")
async def onboarding_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    record = _get_onboarding(svc, current.tenant_id)
    if not record:
        return {"onboarding": None, "steps": ONBOARDING_STEPS}
    return {"onboarding": record, "steps": ONBOARDING_STEPS}


@router.post("/onboarding/step/{step_id}/complete")
async def onboarding_step_complete(
    step_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)

    record = _get_onboarding(svc, current.tenant_id)
    if not record:
        raise HTTPException(status_code=404, detail="Onboarding not started")

    rdata = dict(record.get("data") or {})
    step_status: dict[str, str] = dict(rdata.get("step_status_json") or {})

    valid_step_ids = {s["id"] for s in ONBOARDING_STEPS}
    if step_id not in valid_step_ids:
        raise HTTPException(status_code=422, detail=f"Invalid step_id: {step_id}")

    if step_id == "7":
        active_pack = _get_active_pack(svc, current.tenant_id)
        if not active_pack:
            raise HTTPException(status_code=422, detail="An active NERIS pack is required before completing step 7.")
        dept_id_str = rdata.get("department_id")
        if dept_id_str:
            try:
                dept_id = uuid.UUID(dept_id_str)
                exporter = _exporter(db, current)
                entity_payload = exporter.build_entity_payload(dept_id)
                pack_id = uuid.UUID(str(active_pack["id"]))
                validator = _validator(db, current)
                entity_issues = validator.validate(pack_id=pack_id, entity_type="ENTITY", payload=entity_payload)
                errors = [i for i in entity_issues if i.get("severity") == "error"]
                if errors:
                    raise HTTPException(status_code=422, detail={"message": "Entity validation must pass before completing step 7.", "issues": errors})
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid department_id in onboarding record.")

    step_status[step_id] = "complete"
    step_data = payload.get("data", {})
    if step_data:
        rdata[f"step_{step_id}_data"] = step_data
    rdata["step_status_json"] = step_status
    rdata["current_step"] = str(min(int(step_id) + 1, len(ONBOARDING_STEPS)))

    all_complete = all(step_status.get(s["id"]) == "complete" for s in ONBOARDING_STEPS)
    if all_complete:
        rdata["completed_at"] = datetime.now(UTC).isoformat()

    updated = await svc.update(
        table="neris_onboarding",
        tenant_id=current.tenant_id,
        record_id=uuid.UUID(str(record["id"])),
        actor_user_id=current.user_id,
        patch=rdata,
        expected_version=record.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return {"onboarding": updated, "step_id": step_id, "all_complete": all_complete}


@router.post("/validate/entity")
async def validate_entity(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    dept_id_str = payload.get("department_id")
    if not dept_id_str:
        raise HTTPException(status_code=422, detail="department_id is required")
    try:
        dept_id = uuid.UUID(dept_id_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid department_id")

    svc = _svc(db)
    active_pack = _get_active_pack(svc, current.tenant_id)
    if not active_pack:
        raise HTTPException(status_code=422, detail="No active NERIS pack found. Import and activate a pack first.")

    exporter = _exporter(db, current)
    try:
        entity_payload = exporter.build_entity_payload(dept_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    pack_id = uuid.UUID(str(active_pack["id"]))
    issues = _validator(db, current).validate(pack_id=pack_id, entity_type="ENTITY", payload=entity_payload)
    return {"valid": len([i for i in issues if i.get("severity") == "error"]) == 0, "issues": issues, "pack_id": str(pack_id)}


@router.post("/validate/incidents/{incident_id}")
async def validate_incident(
    incident_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    active_pack = _get_active_pack(svc, current.tenant_id)
    if not active_pack:
        raise HTTPException(status_code=422, detail="No active NERIS pack found.")

    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    exporter = _exporter(db, current)
    incident_payload = exporter.build_incident_payload(inc)
    pack_id = uuid.UUID(str(active_pack["id"]))
    issues = _validator(db, current).validate(pack_id=pack_id, entity_type="INCIDENT", payload=incident_payload)
    return {"valid": len([i for i in issues if i.get("severity") == "error"]) == 0, "issues": issues, "pack_id": str(pack_id)}


@router.get("/export/entity")
async def export_entity(
    department_id: uuid.UUID = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    _require_onboarding_complete(db, current)
    exporter = _exporter(db, current)
    try:
        entity_payload = exporter.build_entity_payload(department_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return entity_payload


@router.get("/export/incidents")
async def export_incidents(
    department_id: uuid.UUID = Query(...),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    _require_onboarding_complete(db, current)
    svc = _svc(db)
    exporter = _exporter(db, current)
    incidents = svc.repo("fire_incidents").list(tenant_id=current.tenant_id, limit=500)
    incidents = [i for i in incidents if (i.get("data") or {}).get("department_id") == str(department_id)]
    if date_from:
        incidents = [i for i in incidents if (i.get("data") or {}).get("start_datetime", "") >= date_from]
    if date_to:
        incidents = [i for i in incidents if (i.get("data") or {}).get("start_datetime", "") <= date_to]
    return [exporter.build_incident_payload(i) for i in incidents]


@router.post("/export/bundle")
async def export_bundle(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    _require_onboarding_complete(db, current)
    correlation_id = getattr(request.state, "correlation_id", None)

    dept_id_str = payload.get("department_id")
    if not dept_id_str:
        raise HTTPException(status_code=422, detail="department_id is required")
    try:
        dept_id = uuid.UUID(dept_id_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid department_id")

    svc = _svc(db)
    incident_ids_raw: list[str] | None = payload.get("incident_ids")
    date_from: str | None = payload.get("date_from")
    date_to: str | None = payload.get("date_to")

    if incident_ids_raw is not None:
        try:
            incident_ids = [uuid.UUID(i) for i in incident_ids_raw]
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid UUID in incident_ids")
    else:
        incidents = svc.repo("fire_incidents").list(tenant_id=current.tenant_id, limit=500)
        incidents = [i for i in incidents if (i.get("data") or {}).get("department_id") == str(dept_id)]
        if date_from:
            incidents = [i for i in incidents if (i.get("data") or {}).get("start_datetime", "") >= date_from]
        if date_to:
            incidents = [i for i in incidents if (i.get("data") or {}).get("start_datetime", "") <= date_to]
        incident_ids = [uuid.UUID(str(i["id"])) for i in incidents]

    exporter = _exporter(db, current)
    return await exporter.generate_bundle(department_id=dept_id, incident_ids=incident_ids, correlation_id=correlation_id)


def _require_onboarding_complete(db: Session, current: CurrentUser) -> None:
    svc = _svc(db)
    record = _get_onboarding(svc, current.tenant_id)
    if not record:
        raise HTTPException(status_code=422, detail="Onboarding not started. Complete onboarding before exporting.")
    rdata = record.get("data") or {}
    step_status = rdata.get("step_status_json") or {}
    if step_status.get("7") != "complete":
        raise HTTPException(status_code=422, detail="Onboarding step 7 must be completed before exporting.")
