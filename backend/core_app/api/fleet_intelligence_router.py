from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.fleet.fault_detector import FaultDetector
from core_app.fleet.readiness_engine import ReadinessEngine
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/fleet-intelligence", tags=["Fleet Intelligence"])

ALLOWED_ROLES = {"founder", "agency_admin", "admin", "dispatcher", "ems"}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/readiness/fleet")
async def fleet_readiness(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    engine = ReadinessEngine(db, get_event_publisher(), current.tenant_id, current.user_id)
    return engine.fleet_summary()


@router.get("/readiness/units/{unit_id}")
async def unit_readiness(
    unit_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    engine = ReadinessEngine(db, get_event_publisher(), current.tenant_id, current.user_id)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await engine.persist_readiness(unit_id, correlation_id=correlation_id)


@router.post("/obd/analyze")
async def analyze_obd(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    unit_id_str = payload.get("unit_id")
    if not unit_id_str:
        raise HTTPException(status_code=422, detail="unit_id is required")
    try:
        unit_id = uuid.UUID(unit_id_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="unit_id must be a valid UUID")
    obd_data = payload.get("obd", payload)
    correlation_id = getattr(request.state, "correlation_id", None)
    detector = FaultDetector(db, get_event_publisher(), current.tenant_id, current.user_id)
    return await detector.process_and_store(unit_id, obd_data, correlation_id=correlation_id)


@router.get("/alerts")
async def list_alerts(
    unit_id: str | None = None,
    severity: str | None = None,
    unresolved_only: bool = True,
    limit: int = 100,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    alerts = svc.repo("fleet_alerts").list(tenant_id=current.tenant_id, limit=min(limit, 500))
    if unit_id:
        alerts = [a for a in alerts if (a.get("data") or {}).get("unit_id") == unit_id]
    if severity:
        alerts = [a for a in alerts if (a.get("data") or {}).get("severity") == severity]
    if unresolved_only:
        alerts = [a for a in alerts if not (a.get("data") or {}).get("resolved")]
    return alerts


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    alert = svc.repo("fleet_alerts").get(tenant_id=current.tenant_id, record_id=alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    data = dict(alert.get("data") or {})
    data["resolved"] = True
    data["acknowledged"] = True
    data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    data["resolved_by"] = str(current.user_id)
    data["resolution_note"] = payload.get("note")
    updated = await svc.update(
        table="fleet_alerts",
        tenant_id=current.tenant_id,
        record_id=alert_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=alert.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return updated


@router.post("/maintenance/work-orders")
async def create_work_order(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    unit_id = payload.get("unit_id")
    if not unit_id:
        raise HTTPException(status_code=422, detail="unit_id is required")
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="maintenance_work_orders",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "unit_id": str(unit_id),
            "title": payload.get("title", ""),
            "description": payload.get("description", ""),
            "priority": payload.get("priority", "routine"),
            "status": "open",
            "assigned_to": payload.get("assigned_to"),
            "due_date": payload.get("due_date"),
            "estimated_hours": payload.get("estimated_hours"),
            "source_alert_id": payload.get("source_alert_id"),
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        },
        correlation_id=correlation_id,
    )


@router.get("/maintenance/work-orders")
async def list_work_orders(
    unit_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    orders = svc.repo("maintenance_work_orders").list(tenant_id=current.tenant_id, limit=min(limit, 500))
    if unit_id:
        orders = [o for o in orders if (o.get("data") or {}).get("unit_id") == unit_id]
    if status:
        orders = [o for o in orders if (o.get("data") or {}).get("status") == status]
    return orders


@router.patch("/maintenance/work-orders/{order_id}")
async def update_work_order(
    order_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    order = svc.repo("maintenance_work_orders").get(tenant_id=current.tenant_id, record_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Work order not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    data = dict(order.get("data") or {})
    for field in ("status", "title", "description", "priority", "assigned_to", "due_date", "estimated_hours", "actual_hours", "notes"):
        if field in payload:
            data[field] = payload[field]
    if payload.get("status") == "completed" and not data.get("completed_at"):
        data["completed_at"] = datetime.now(timezone.utc).isoformat()
    updated = await svc.update(
        table="maintenance_work_orders",
        tenant_id=current.tenant_id,
        record_id=order_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=order.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return updated


@router.post("/inspections/templates")
async def create_inspection_template(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="inspection_templates",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "name": payload.get("name", ""),
            "vehicle_type": payload.get("vehicle_type", "ground"),
            "frequency": payload.get("frequency", "daily"),
            "items": payload.get("items", []),
            "active": True,
        },
        correlation_id=correlation_id,
    )


@router.get("/inspections/templates")
async def list_inspection_templates(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    return svc.repo("inspection_templates").list(tenant_id=current.tenant_id, limit=200)


@router.post("/inspections/instances")
async def create_inspection_instance(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="inspection_instances",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "template_id": payload.get("template_id"),
            "unit_id": payload.get("unit_id"),
            "inspected_by": str(current.user_id),
            "inspected_at": datetime.now(timezone.utc).isoformat(),
            "responses": payload.get("responses", {}),
            "passed": payload.get("passed", True),
            "failures": payload.get("failures", []),
            "notes": payload.get("notes"),
        },
        correlation_id=correlation_id,
    )
