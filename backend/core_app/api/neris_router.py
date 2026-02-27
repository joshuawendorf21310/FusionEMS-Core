from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.neris.copilot import NERISCopilot
from core_app.neris.exporter import NERISExporter
from core_app.neris.pack_manager import NERISPackManager
from core_app.neris.validator import NERISValidator
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/neris", tags=["NERIS"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _get_active_pack(svc: DominationService, tenant_id: uuid.UUID) -> dict[str, Any] | None:
    packs = svc.repo("neris_packs").list(tenant_id=tenant_id, limit=100)
    for p in packs:
        if (p.get("data") or {}).get("status") == "active":
            return p
    return None


@router.post("/validate")
async def validate(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    active_pack = _get_active_pack(svc, current.tenant_id)
    if not active_pack:
        raise HTTPException(status_code=422, detail="No active NERIS pack found. Import and activate a pack first.")
    pack_id = uuid.UUID(str(active_pack["id"]))
    entity_type = payload.get("entity_type", "INCIDENT")
    data = payload.get("payload", payload)
    validator = NERISValidator(db, get_event_publisher(), current.tenant_id)
    issues = validator.validate(pack_id=pack_id, entity_type=entity_type, payload=data)
    errors = [i for i in issues if i.get("severity") == "error"]
    result = {"valid": len(errors) == 0, "issues": issues, "pack_id": str(pack_id)}
    correlation_id = getattr(request.state, "correlation_id", None)
    record = await svc.create(
        table="neris_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "entity_type": entity_type},
        correlation_id=correlation_id,
    )
    return {**result, "record_id": str(record["id"])}


@router.post("/exports")
async def create_export(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    active_pack = _get_active_pack(svc, current.tenant_id)
    if not active_pack:
        raise HTTPException(status_code=422, detail="No active NERIS pack found.")
    correlation_id = getattr(request.state, "correlation_id", None)
    dept_id_str = payload.get("department_id")
    incident_ids_raw = payload.get("incident_ids", [])
    if not dept_id_str:
        raise HTTPException(status_code=422, detail="department_id is required")
    try:
        dept_id = uuid.UUID(dept_id_str)
        incident_ids = [uuid.UUID(i) for i in incident_ids_raw]
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid UUID: {exc}")
    exporter = NERISExporter(db, get_event_publisher(), current.tenant_id, current.user_id)
    result = await exporter.generate_bundle(
        department_id=dept_id,
        incident_ids=incident_ids,
        correlation_id=correlation_id,
    )
    return result


@router.get("/exports/{job_id}")
async def get_export(
    job_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = svc.repo("neris_export_jobs").get(tenant_id=current.tenant_id, record_id=job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    return rec
