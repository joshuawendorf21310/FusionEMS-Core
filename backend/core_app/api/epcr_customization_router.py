from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role
from core_app.epcr.completeness_engine import ELEMENT_FIELD_MAP
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/epcr/customize", tags=["ePCR Customization"])

_NEMSIS_REQUIRED_PATHS: set[str] = {meta["path"] for meta in ELEMENT_FIELD_MAP.values()}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


@router.post("/branding")
async def save_branding(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    rec = await _svc(db).create(
        table="epcr_agency_branding",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "logo_url": payload.get("logo_url", ""),
            "primary_color": payload.get("primary_color", ""),
            "secondary_color": payload.get("secondary_color", ""),
            "theme": payload.get("theme", "light"),
            "agency_name": payload.get("agency_name", ""),
            "active": True,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return rec


@router.get("/branding")
async def get_branding(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    all_records = _svc(db).repo("epcr_agency_branding").list(tenant_id=current.tenant_id)
    active = [r for r in all_records if r.get("data", {}).get("active")]
    return active[0] if active else {}


@router.post("/layouts")
async def save_layout(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    rec = await _svc(db).create(
        table="epcr_form_layouts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "name": payload.get("name", ""),
            "mode": payload.get("mode", "bls"),
            "sections_order": payload.get("sections_order", []),
            "hidden_fields": payload.get("hidden_fields", []),
            "role": payload.get("role", ""),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return rec


@router.get("/layouts")
async def list_layouts(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("epcr_form_layouts").list(tenant_id=current.tenant_id)


@router.get("/layouts/{layout_id}")
async def get_layout(
    layout_id: str,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_form_layouts").get(tenant_id=current.tenant_id, record_id=layout_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Layout not found")
    return rec


@router.patch("/layouts/{layout_id}")
async def update_layout(
    layout_id: str,
    patch: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = svc.repo("epcr_form_layouts").get(tenant_id=current.tenant_id, record_id=layout_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Layout not found")

    hidden_fields: list[str] = patch.get("hidden_fields", rec.get("data", {}).get("hidden_fields", []))
    for field in hidden_fields:
        if field in _NEMSIS_REQUIRED_PATHS:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot hide WI-required field: {field}. Hiding this field would break NEMSIS compliance.",
            )

    updated_data = {**rec["data"], **patch}
    updated_rec = await svc.update(
        table="epcr_form_layouts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if updated_rec is None:
        raise HTTPException(status_code=409, detail="Version conflict")
    return updated_rec


@router.post("/rules")
async def save_rule(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    rec = await _svc(db).create(
        table="epcr_customization_rules",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "trigger_field": payload.get("trigger_field", ""),
            "trigger_value": payload.get("trigger_value", ""),
            "action": payload.get("action", ""),
            "target_field": payload.get("target_field", ""),
            "message": payload.get("message", ""),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return rec


@router.get("/rules")
async def list_rules(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("epcr_customization_rules").list(tenant_id=current.tenant_id)


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    repo = _svc(db).repo("epcr_customization_rules")
    deleted = repo.soft_delete(tenant_id=current.tenant_id, record_id=uuid.UUID(rule_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"deleted": True, "rule_id": rule_id}


@router.post("/picklists")
async def save_picklist(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    rec = await _svc(db).create(
        table="epcr_picklist_items",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "list_name": payload.get("list_name", ""),
            "items": payload.get("items", []),
            "category": payload.get("category", ""),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return rec


@router.get("/picklists")
async def list_picklists(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("epcr_picklist_items").list(tenant_id=current.tenant_id)


@router.get("/picklists/{list_name}")
async def get_picklist(
    list_name: str,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    all_records = _svc(db).repo("epcr_picklist_items").list(tenant_id=current.tenant_id)
    matched = [r for r in all_records if r.get("data", {}).get("list_name") == list_name]
    if not matched:
        raise HTTPException(status_code=404, detail="Picklist not found")
    items: list[str] = []
    for r in matched:
        items.extend(r.get("data", {}).get("items", []))
    return {"list_name": list_name, "items": items}
