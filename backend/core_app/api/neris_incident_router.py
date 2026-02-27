from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.neris.pack_manager import NERISPackManager
from core_app.neris.validator import NERISValidator
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/incidents/fire", tags=["Fire Incidents"])

ALLOWED_ROLES = {"agency_admin", "ems", "founder", "admin"}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check_role(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


def _get_active_pack(svc: DominationService, tenant_id: uuid.UUID) -> dict[str, Any] | None:
    packs = svc.repo("neris_packs").list(tenant_id=tenant_id, limit=100)
    for p in packs:
        if (p.get("data") or {}).get("status") == "active":
            return p
    return None


@router.post("/")
async def create_incident(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    correlation_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)
    dept_id = payload.get("department_id")
    if not dept_id:
        raise HTTPException(status_code=422, detail="department_id is required")
    active_pack = _get_active_pack(svc, current.tenant_id)
    return await svc.create(
        table="fire_incidents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "department_id": str(dept_id),
            "incident_number": payload.get("incident_number", ""),
            "start_datetime": payload.get("start_datetime", ""),
            "end_datetime": payload.get("end_datetime"),
            "incident_type_code": payload.get("incident_type_code", ""),
            "location_json": payload.get("location_json", {}),
            "property_use_code": payload.get("property_use_code"),
            "status": "draft",
            "neris_pack_id": str(active_pack["id"]) if active_pack else None,
        },
        correlation_id=correlation_id,
    )


@router.get("/")
async def list_incidents(
    department_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    incidents = svc.repo("fire_incidents").list(tenant_id=current.tenant_id, limit=limit)
    if department_id:
        incidents = [i for i in incidents if (i.get("data") or {}).get("department_id") == department_id]
    if status:
        incidents = [i for i in incidents if (i.get("data") or {}).get("status") == status]
    return incidents


@router.get("/pack-rules")
async def get_pack_rules(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    active_pack = _get_active_pack(svc, current.tenant_id)
    if not active_pack:
        raise HTTPException(status_code=404, detail="No active NERIS pack found")
    pack_id = uuid.UUID(str(active_pack["id"]))
    all_rules = svc.repo("neris_compiled_rules").list(tenant_id=current.tenant_id, limit=50)
    for r in all_rules:
        rd = r.get("data") or {}
        if rd.get("pack_id") == str(pack_id) and rd.get("entity_type") == "INCIDENT":
            return rd.get("rules_json", {})
    raise HTTPException(status_code=404, detail="Compiled INCIDENT rules not found for active pack")


@router.get("/departments/{department_id}/apparatus")
async def list_apparatus(
    department_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    all_apparatus = svc.repo("fire_apparatus").list(tenant_id=current.tenant_id, limit=200)
    return [a for a in all_apparatus if (a.get("data") or {}).get("department_id") == str(department_id)]


@router.get("/{incident_id}")
async def get_incident(
    incident_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc_id = str(incident_id)
    units = svc.repo("fire_incident_units").list(tenant_id=current.tenant_id, limit=50)
    actions = svc.repo("fire_incident_actions").list(tenant_id=current.tenant_id, limit=50)
    outcomes_list = svc.repo("fire_incident_outcomes").list(tenant_id=current.tenant_id, limit=5)
    return {
        "incident": inc,
        "units": [u for u in units if (u.get("data") or {}).get("incident_id") == inc_id],
        "actions": [a for a in actions if (a.get("data") or {}).get("incident_id") == inc_id],
        "outcomes": next((o for o in outcomes_list if (o.get("data") or {}).get("incident_id") == inc_id), None),
    }


@router.patch("/{incident_id}")
async def update_incident(
    incident_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    current_data = dict(inc.get("data") or {})
    allowed_fields = {"incident_number", "start_datetime", "end_datetime", "incident_type_code", "location_json", "property_use_code", "status", "neris_pack_id"}
    for k, v in payload.items():
        if k in allowed_fields:
            current_data[k] = v
    updated = await svc.update(
        table="fire_incidents",
        tenant_id=current.tenant_id,
        record_id=incident_id,
        actor_user_id=current.user_id,
        patch=current_data,
        expected_version=inc.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return updated


@router.delete("/{incident_id}")
async def delete_incident(
    incident_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    current_data = dict(inc.get("data") or {})
    current_data["status"] = "deleted"
    updated = await svc.update(
        table="fire_incidents",
        tenant_id=current.tenant_id,
        record_id=incident_id,
        actor_user_id=current.user_id,
        patch=current_data,
        expected_version=inc.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return {"deleted": True, "incident_id": str(incident_id)}


@router.post("/{incident_id}/units")
async def add_unit(
    incident_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    apparatus_id = payload.get("apparatus_id")
    unit_id = payload.get("unit_id")
    if not unit_id:
        raise HTTPException(status_code=422, detail="unit_id is required")
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="fire_incident_units",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "incident_id": str(incident_id),
            "apparatus_id": str(apparatus_id) if apparatus_id else None,
            "unit_id": unit_id,
            "arrival_datetime": payload.get("arrival_datetime"),
            "departure_datetime": payload.get("departure_datetime"),
        },
        correlation_id=correlation_id,
    )


@router.delete("/{incident_id}/units/{unit_id}")
async def remove_unit(
    incident_id: uuid.UUID,
    unit_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    deleted = svc.repo("fire_incident_units").soft_delete(tenant_id=current.tenant_id, record_id=unit_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Unit not found")
    return {"deleted": True, "unit_id": str(unit_id)}


@router.post("/{incident_id}/actions")
async def add_action(
    incident_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    action_code = payload.get("action_code")
    if not action_code:
        raise HTTPException(status_code=422, detail="action_code is required")
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="fire_incident_actions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "incident_id": str(incident_id),
            "action_code": action_code,
            "action_datetime": payload.get("action_datetime"),
        },
        correlation_id=correlation_id,
    )


@router.put("/{incident_id}/outcomes")
async def upsert_outcomes(
    incident_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    outcomes_data = {
        "incident_id": str(incident_id),
        "outcomes_json": {
            "civilian_injuries": payload.get("civilian_injuries", 0),
            "civilian_fatalities": payload.get("civilian_fatalities", 0),
            "firefighter_injuries": payload.get("firefighter_injuries", 0),
            "firefighter_fatalities": payload.get("firefighter_fatalities", 0),
            "property_loss_estimate": payload.get("property_loss_estimate"),
            "contents_loss_estimate": payload.get("contents_loss_estimate"),
        },
    }

    existing_list = svc.repo("fire_incident_outcomes").list(tenant_id=current.tenant_id, limit=5)
    existing = next((o for o in existing_list if (o.get("data") or {}).get("incident_id") == str(incident_id)), None)

    if existing:
        updated = await svc.update(
            table="fire_incident_outcomes",
            tenant_id=current.tenant_id,
            record_id=uuid.UUID(str(existing["id"])),
            actor_user_id=current.user_id,
            patch=outcomes_data,
            expected_version=existing.get("version", 1),
            correlation_id=correlation_id,
        )
        if updated is None:
            raise HTTPException(status_code=409, detail="Version conflict, please retry")
        return updated
    else:
        return await svc.create(
            table="fire_incident_outcomes",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data=outcomes_data,
            correlation_id=correlation_id,
        )


@router.post("/{incident_id}/validate")
async def validate_incident(
    incident_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    svc = _svc(db)
    active_pack = _get_active_pack(svc, current.tenant_id)
    if not active_pack:
        raise HTTPException(status_code=422, detail="No active NERIS pack found. Import and activate a pack first.")

    inc = svc.repo("fire_incidents").get(tenant_id=current.tenant_id, record_id=incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    from core_app.neris.exporter import NERISExporter
    exporter = NERISExporter(db, get_event_publisher(), current.tenant_id, current.user_id)
    incident_payload = exporter.build_incident_payload(inc)

    pack_id = uuid.UUID(str(active_pack["id"]))
    validator = NERISValidator(db, get_event_publisher(), current.tenant_id)
    issues = validator.validate(pack_id=pack_id, entity_type="INCIDENT", payload=incident_payload)
    errors = [i for i in issues if i.get("severity") == "error"]
    valid = len(errors) == 0

    if valid:
        correlation_id = getattr(request.state, "correlation_id", None)
        current_data = dict(inc.get("data") or {})
        current_data["status"] = "validated"
        current_data["validated_at"] = datetime.now(timezone.utc).isoformat()
        current_data["neris_pack_id"] = str(pack_id)
        await svc.update(
            table="fire_incidents",
            tenant_id=current.tenant_id,
            record_id=incident_id,
            actor_user_id=current.user_id,
            patch=current_data,
            expected_version=inc.get("version", 1),
            correlation_id=correlation_id,
        )

    return {"valid": valid, "issues": issues}
