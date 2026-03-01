from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/pricebooks", tags=["Pricebooks"])

PRICING_CATALOG = {
    "SCHEDULING_ONLY": [
        {"tier": "S1", "label": "1–25 users", "monthly_cents": 19900},
        {"tier": "S2", "label": "26–75 users", "monthly_cents": 39900},
        {"tier": "S3", "label": "76–150 users", "monthly_cents": 69900},
    ],
    "BILLING_AUTOMATION": [
        {"tier": "B1", "label": "0–150 claims", "base_monthly_cents": 39900, "per_claim_cents": 600},
        {"tier": "B2", "label": "151–400 claims", "base_monthly_cents": 59900, "per_claim_cents": 500},
        {"tier": "B3", "label": "401–1000 claims", "base_monthly_cents": 99900, "per_claim_cents": 400},
        {"tier": "B4", "label": "1001+ claims", "base_monthly_cents": 149900, "per_claim_cents": 325},
    ],
    "ADDONS": [
        {"code": "CCT_TRANSPORT_OPS", "label": "CCT/Transport Ops", "monthly_cents": 39900},
        {"code": "HEMS_OPS", "label": "HEMS Ops", "monthly_cents": 75000},
        {"code": "TRIP_PACK", "label": "Wisconsin TRIP Pack", "monthly_cents": 19900, "gov_only": True},
    ],
}

PLAN_CODES = {"SCHEDULING_ONLY", "OPS_CORE", "CLINICAL_CORE", "FULL_STACK"}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


@router.get("/catalog")
async def get_catalog(current: CurrentUser = Depends(require_role("founder", "agency_admin"))):
    return PRICING_CATALOG


@router.get("/")
async def list_pricebooks(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    return svc.repo("pricebooks").list(tenant_id=current.tenant_id, limit=50)


@router.post("/")
async def create_pricebook(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="pricebooks",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "name": payload.get("name", ""),
            "region": payload.get("region", "WI"),
            "status": "draft",
            "items": payload.get("items", PRICING_CATALOG),
            "effective_date": payload.get("effective_date"),
            "notes": payload.get("notes"),
            "created_by": str(current.user_id),
        },
        correlation_id=correlation_id,
    )


@router.post("/{pb_id}/activate")
async def activate_pricebook(
    pb_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    pb = svc.repo("pricebooks").get(tenant_id=current.tenant_id, record_id=pb_id)
    if not pb:
        raise HTTPException(status_code=404, detail="Pricebook not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    all_pbs = svc.repo("pricebooks").list(tenant_id=current.tenant_id, limit=50)
    for p in all_pbs:
        if (p.get("data") or {}).get("status") == "active" and str(p["id"]) != str(pb_id):
            pd = dict(p.get("data") or {})
            pd["status"] = "archived"
            await svc.update(
                table="pricebooks",
                tenant_id=current.tenant_id,
                record_id=uuid.UUID(str(p["id"])),
                actor_user_id=current.user_id,
                patch=pd,
                expected_version=p.get("version", 1),
                correlation_id=correlation_id,
            )
    data = dict(pb.get("data") or {})
    data["status"] = "active"
    data["activated_at"] = datetime.now(UTC).isoformat()
    updated = await svc.update(
        table="pricebooks",
        tenant_id=current.tenant_id,
        record_id=pb_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=pb.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return updated


@router.get("/active")
async def get_active_pricebook(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    pbs = svc.repo("pricebooks").list(tenant_id=current.tenant_id, limit=50)
    active = next((p for p in pbs if (p.get("data") or {}).get("status") == "active"), None)
    if not active:
        return {"active": False, "catalog": PRICING_CATALOG}
    return {"active": True, "pricebook": active}


@router.get("/entitlements/{tenant_id}")
async def get_entitlements(
    tenant_id: uuid.UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    records = svc.repo("entitlements").list(tenant_id=tenant_id, limit=10)
    if not records:
        return {"tenant_id": str(tenant_id), "plan_code": None, "modules": [], "configured": False}
    latest = sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)[0]
    return latest


@router.post("/entitlements")
async def set_entitlements(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    target_tenant = uuid.UUID(payload.get("tenant_id") or str(current.tenant_id))
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="entitlements",
        tenant_id=target_tenant,
        actor_user_id=current.user_id,
        data={
            "plan_code": payload.get("plan_code"),
            "tier_code": payload.get("tier_code"),
            "modules": payload.get("modules", []),
            "addons": payload.get("addons", []),
            "stripe_subscription_id": payload.get("stripe_subscription_id"),
            "is_government_entity": payload.get("is_government_entity", False),
            "collections_mode": payload.get("collections_mode", "none"),
            "trip_enabled": payload.get("trip_enabled", False),
            "active": True,
            "set_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=correlation_id,
    )
