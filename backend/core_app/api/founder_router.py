from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/founder", tags=['Founder'])


@router.get("/tenants", dependencies=[Depends(require_role("founder","admin"))])
async def tenants(request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    scores = svc.repo("governance_scores").list(tenant_id=current.tenant_id, limit=50, offset=0)
    return [{"tenant_id": str(current.tenant_id), "governance_scores": scores}]

@router.get("/tenants/{tenant_id}/billing", dependencies=[Depends(require_role("founder","admin","billing"))])
async def tenant_billing(tenant_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return {"billing_jobs": svc.repo("billing_jobs").list(tenant_id=current.tenant_id, limit=200, offset=0), "claims": svc.repo("claims").list(tenant_id=current.tenant_id, limit=200, offset=0)}

@router.get("/tenants/{tenant_id}/compliance", dependencies=[Depends(require_role("founder","admin"))])
async def tenant_compliance(tenant_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return {"nemsis": svc.repo("nemsis_validation_results").list(tenant_id=current.tenant_id, limit=50, offset=0),
            "neris": svc.repo("neris_validation_results").list(tenant_id=current.tenant_id, limit=50, offset=0),
            "scores": svc.repo("governance_scores").list(tenant_id=current.tenant_id, limit=50, offset=0)}

@router.post("/support/impersonate/start", dependencies=[Depends(require_role("founder"))])
async def impersonate(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="support_sessions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"type":"impersonate", **payload}, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/support/session/start", dependencies=[Depends(require_role("founder"))])
async def support_session(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="support_sessions", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"type":"remote_support", **payload}, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/ai/chat", dependencies=[Depends(require_role("founder","admin"))])
async def ai_chat(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    run = {"prompt": payload.get("message"), "model": payload.get("model","gpt-4.1"), "status":"queued"}
    return await svc.create(table="ai_runs", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=run, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/docs/generate", dependencies=[Depends(require_role("founder","admin"))])
async def docs(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user)):
    return {"status":"accepted","kind":payload.get("kind"),"name":payload.get("name")}


@router.get("/dashboard")
async def founder_dashboard(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())

    tenants_list = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=10000)
    active_tenants = [t for t in tenants_list if t.get("data", {}).get("status") == "active"]

    subscriptions = svc.repo("tenant_subscriptions").list(tenant_id=current.tenant_id, limit=10000)
    mrr = sum(int(s.get("data", {}).get("monthly_amount_cents", 0)) for s in subscriptions
              if s.get("data", {}).get("status") == "active")

    return {
        "mrr_cents": mrr,
        "tenant_count": len(active_tenants),
        "error_count_1h": 0,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/webhook-health")
async def webhook_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())

    health: dict[str, str] = {}
    sources = ["stripe", "lob", "telnyx", "officeally"]

    for source in sources:
        try:
            dead_items = [
                r for r in svc.repo("webhook_dlq").list(tenant_id=current.tenant_id, limit=100)
                if r.get("data", {}).get("source") == source
                and r.get("data", {}).get("status") == "dead"
            ]
            health[source] = "error" if dead_items else "ok"
        except Exception:
            health[source] = "unknown"

    return {"health": health, "as_of": datetime.now(timezone.utc).isoformat()}


@router.get("/feature-flags")
async def get_feature_flags(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    tenants_list = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=1)
    flags: dict = {}
    if tenants_list:
        flags = tenants_list[0].get("data", {}).get("feature_flags", {})
    return {"flags": flags}


@router.patch("/feature-flags")
async def update_feature_flags(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    tenants_list = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=1)
    if not tenants_list:
        return {"error": "tenant_not_found"}
    tenant = tenants_list[0]
    current_flags = tenant.get("data", {}).get("feature_flags", {})
    updated_flags = {**current_flags, **payload}
    await svc.update(
        table="tenants",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(tenant["id"])),
        expected_version=tenant.get("version", 1),
        patch={"feature_flags": updated_flags},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"flags": updated_flags, "updated": True}


@router.get("/aws-cost")
async def aws_cost_summary(
    current: CurrentUser = Depends(get_current_user),
):
    require_role(current, ["founder"])
    try:
        import boto3
        from core_app.core.config import get_settings
        settings = get_settings()
        client = boto3.client("ce", region_name=settings.aws_region or "us-east-1")
        from datetime import date, timedelta
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=30)).isoformat()
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        results = []
        for period in resp.get("ResultsByTime", []):
            for group in period.get("Groups", []):
                results.append({
                    "service": group["Keys"][0],
                    "amount": float(group["Metrics"]["UnblendedCost"]["Amount"]),
                    "unit": group["Metrics"]["UnblendedCost"]["Unit"],
                })
        total = sum(r["amount"] for r in results)
        return {"period": f"{start} to {end}", "total_usd": round(total, 2), "by_service": results}
    except Exception as e:
        return {"error": str(e), "message": "AWS Cost Explorer not available"}


@router.get("/compliance/status")
async def compliance_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    from core_app.services.domination_service import DominationService
    from core_app.services.event_publisher import get_event_publisher
    from sqlalchemy.orm import Session as _Session

    svc = DominationService(db, get_event_publisher())

    nemsis_jobs = svc.repo("nemsis_export_jobs").list(tenant_id=current.tenant_id, limit=1)
    nemsis_latest = nemsis_jobs[0] if nemsis_jobs else None

    neris_jobs = svc.repo("neris_export_jobs").list(tenant_id=current.tenant_id, limit=1)
    neris_latest = neris_jobs[0] if neris_jobs else None

    packs = svc.repo("compliance_packs").list(tenant_id=current.tenant_id, limit=100)
    active_packs = [p for p in packs if (p.get("data") or {}).get("active")]

    return {
        "nemsis": {
            "certified": nemsis_latest is not None,
            "last_export_at": (nemsis_latest or {}).get("created_at"),
            "status": (nemsis_latest or {}).get("data", {}).get("status", "none"),
        },
        "neris": {
            "onboarded": neris_latest is not None,
            "last_export_at": (neris_latest or {}).get("created_at"),
            "status": (neris_latest or {}).get("data", {}).get("status", "none"),
        },
        "compliance_packs": {
            "active_count": len(active_packs),
            "packs": [{"id": p.get("id"), "name": (p.get("data") or {}).get("name")} for p in active_packs],
        },
        "overall": "partial" if (nemsis_latest or neris_latest or active_packs) else "none",
    }
