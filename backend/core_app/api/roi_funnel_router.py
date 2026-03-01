from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.roi.engine import compute_roi
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/roi-funnel", tags=["ROI + Self-Service Funnel"])


class FunnelROIRequest(BaseModel):
    zip_code: str
    call_volume: int = 0
    payer_mix: dict[str, float] = Field(default_factory=dict)
    current_billing_pct: float = 0.0
    years: int = 3
    agency_name: str = ""
    selected_modules: list[str] = Field(default_factory=list)
    service_levels: list[str] = Field(default_factory=list)


class ConversionEventRequest(BaseModel):
    event_type: str
    funnel_stage: str
    session_id: str = ""
    metadata: dict = Field(default_factory=dict)


class LeadScoringRequest(BaseModel):
    agency_name: str
    zip_code: str
    call_volume: int
    payer_mix: dict[str, float] = Field(default_factory=dict)
    source: str = "web"
    intent_signals: list[str] = Field(default_factory=list)


class ProposalRequest(BaseModel):
    roi_scenario_id: str
    agency_name: str
    contact_name: str = ""
    contact_email: str = ""
    expiration_days: int = 30
    include_modules: list[str] = Field(default_factory=list)


class PricingSimRequest(BaseModel):
    base_plan: str = "standard"
    modules: list[str] = Field(default_factory=list)
    call_volume: int = 0
    contract_length_months: int = 12


class SubscriptionActivationRequest(BaseModel):
    tenant_id: uuid.UUID
    plan: str
    modules: list[str] = Field(default_factory=list)
    billing_start: str = ""
    stripe_payment_method: str = ""


class BAASigningRequest(BaseModel):
    tenant_id: uuid.UUID
    signer_name: str
    signer_email: str
    signer_title: str = ""


@router.post("/roi-estimate")
async def roi_estimate(
    body: FunnelROIRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    inputs = body.model_dump()
    outputs = compute_roi(inputs)
    svc = DominationService(db, get_event_publisher())
    record = await svc.create(
        table="roi_funnel_scenarios",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"inputs": inputs, "outputs": outputs, "agency_name": body.agency_name},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"id": record["id"], "inputs": inputs, "outputs": outputs}


@router.get("/roi-estimate/{scenario_id}")
async def get_roi_scenario(
    scenario_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("roi_funnel_scenarios").get(tenant_id=current.tenant_id, record_id=scenario_id)
    if not record:
        raise HTTPException(status_code=404, detail="scenario_not_found")
    return record


@router.post("/roi-estimate/{scenario_id}/recalculate")
async def recalculate_roi(
    scenario_id: uuid.UUID,
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("roi_funnel_scenarios").get(tenant_id=current.tenant_id, record_id=scenario_id)
    if not record:
        raise HTTPException(status_code=404, detail="scenario_not_found")
    existing_inputs = record.get("data", {}).get("inputs", {})
    merged_inputs = {**existing_inputs, **body}
    new_outputs = compute_roi(merged_inputs)
    await svc.update(
        table="roi_funnel_scenarios",
        tenant_id=current.tenant_id,
        record_id=record["id"],
        actor_user_id=current.user_id,
        expected_version=record.get("version", 1),
        patch={"inputs": merged_inputs, "outputs": new_outputs},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"id": str(scenario_id), "outputs": new_outputs}


@router.get("/zip-revenue/{zip_code}")
async def zip_revenue(
    zip_code: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    all_scenarios = svc.repo("roi_funnel_scenarios").list(tenant_id=current.tenant_id, limit=10000)
    zip_scenarios = [s for s in all_scenarios if s.get("data", {}).get("inputs", {}).get("zip_code") == zip_code]
    if not zip_scenarios:
        return {"zip_code": zip_code, "scenarios": [], "avg_revenue_uplift_cents": 0}
    revenues = [s.get("data", {}).get("outputs", {}).get("year1_revenue_cents", 0) for s in zip_scenarios]
    avg = round(sum(revenues) / len(revenues)) if revenues else 0
    return {"zip_code": zip_code, "scenario_count": len(zip_scenarios), "avg_revenue_uplift_cents": avg}


@router.post("/conversion-event")
async def track_conversion_event(
    body: ConversionEventRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    record = await svc.create(
        table="conversion_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=body.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.get("/conversion-funnel")
async def conversion_funnel(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    events = svc.repo("conversion_events").list(tenant_id=current.tenant_id, limit=50000)
    stages: dict[str, int] = {}
    for e in events:
        stage = e.get("data", {}).get("funnel_stage", "unknown")
        stages[stage] = stages.get(stage, 0) + 1
    stage_order = ["awareness", "interest", "consideration", "intent", "evaluation", "purchase"]
    funnel = []
    for stage in stage_order:
        funnel.append({"stage": stage, "count": stages.get(stage, 0)})
    for stage, count in stages.items():
        if stage not in stage_order:
            funnel.append({"stage": stage, "count": count})
    return {"funnel": funnel, "total_events": len(events)}


@router.post("/lead-scoring")
async def score_lead(
    body: LeadScoringRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    score = 0
    score += min(body.call_volume / 100, 30)
    score += len(body.intent_signals) * 10
    if body.source == "referral":
        score += 20
    elif body.source == "roi_calculator":
        score += 15
    score = min(round(score), 100)
    tier = "hot" if score >= 70 else ("warm" if score >= 40 else "cold")
    svc = DominationService(db, get_event_publisher())
    record = await svc.create(
        table="lead_scores",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**body.model_dump(), "score": score, "tier": tier},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.post("/proposal")
async def generate_proposal(
    body: ProposalRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    proposal = await svc.create(
        table="proposals",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "roi_scenario_id": body.roi_scenario_id,
            "agency_name": body.agency_name,
            "contact_name": body.contact_name,
            "contact_email": body.contact_email,
            "expiration_days": body.expiration_days,
            "include_modules": body.include_modules,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return proposal


@router.get("/proposal/{proposal_id}")
async def get_proposal(
    proposal_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("proposals").get(tenant_id=current.tenant_id, record_id=proposal_id)
    if not record:
        raise HTTPException(status_code=404, detail="proposal_not_found")
    return record


@router.get("/proposals")
async def list_proposals(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    proposals = svc.repo("proposals").list(tenant_id=current.tenant_id, limit=1000)
    return {"proposals": proposals, "total": len(proposals)}


@router.get("/proposal/{proposal_id}/analytics")
async def proposal_analytics(
    proposal_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    events = svc.repo("conversion_events").list(tenant_id=current.tenant_id, limit=10000)
    views = [e for e in events if e.get("data", {}).get("metadata", {}).get("proposal_id") == str(proposal_id)]
    return {"proposal_id": str(proposal_id), "view_count": len(views)}


@router.post("/pricing-simulation")
async def pricing_simulation(
    body: PricingSimRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    base_prices = {"standard": 49900, "professional": 89900, "enterprise": 149900}
    module_prices = {"billing": 19900, "compliance": 14900, "analytics": 9900, "pwa": 9900}
    base = base_prices.get(body.base_plan, 49900)
    module_cost = sum(module_prices.get(m, 9900) for m in body.modules)
    monthly = base + module_cost
    annual = monthly * 12
    if body.contract_length_months >= 12:
        annual = round(annual * 0.9)
    return {
        "plan": body.base_plan,
        "modules": body.modules,
        "monthly_cents": monthly,
        "annual_cents": annual,
        "annual_savings_pct": 10 if body.contract_length_months >= 12 else 0,
        "cost_per_transport": round(monthly / max(body.call_volume, 1), 2) if body.call_volume else None,
    }


@router.post("/subscription/activate")
async def activate_subscription(
    body: SubscriptionActivationRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    sub = await svc.create(
        table="tenant_subscriptions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "tenant_id": str(body.tenant_id),
            "plan": body.plan,
            "modules": body.modules,
            "billing_start": body.billing_start or datetime.now(UTC).isoformat(),
            "status": "active",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return sub


@router.post("/baa/sign")
async def sign_baa(
    body: BAASigningRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    baa = await svc.create(
        table="baa_signatures",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "tenant_id": str(body.tenant_id),
            "signer_name": body.signer_name,
            "signer_email": body.signer_email,
            "signer_title": body.signer_title,
            "signed_at": datetime.now(UTC).isoformat(),
            "status": "signed",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return baa


@router.get("/onboarding-checklist/{tenant_id}")
async def onboarding_checklist(
    tenant_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    checklist = svc.repo("onboarding_checklists").list(tenant_id=current.tenant_id, limit=100)
    tenant_items = [item for item in checklist if item.get("data", {}).get("tenant_id") == str(tenant_id)]
    completed = sum(1 for item in tenant_items if item.get("data", {}).get("status") == "complete")
    return {
        "tenant_id": str(tenant_id),
        "total_items": len(tenant_items),
        "completed": completed,
        "pending": len(tenant_items) - completed,
        "items": tenant_items,
    }


@router.post("/plan-recommendation")
async def plan_recommendation(
    body: FunnelROIRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    call_volume = body.call_volume
    if call_volume >= 5000:
        plan = "enterprise"
        reason = "High call volume justifies enterprise tier with full module access."
    elif call_volume >= 1000:
        plan = "professional"
        reason = "Mid-tier call volume aligns with professional plan ROI."
    else:
        plan = "standard"
        reason = "Starting plan optimized for smaller agencies."
    outputs = compute_roi(body.model_dump())
    return {
        "recommended_plan": plan,
        "reason": reason,
        "roi_preview": outputs,
        "suggested_modules": ["billing", "compliance"] if call_volume > 500 else ["billing"],
    }


@router.post("/roi-share-link")
async def roi_share_link(
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    token = hashlib.sha256(f"{current.tenant_id}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:16]
    record = await svc.create(
        table="roi_share_links",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"scenario_id": body.get("scenario_id"), "token": token, "expires_at": body.get("expires_at")},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"token": token, "record": record}


@router.get("/conversion-kpis")
async def conversion_kpis(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    events = svc.repo("conversion_events").list(tenant_id=current.tenant_id, limit=50000)
    proposals = svc.repo("proposals").list(tenant_id=current.tenant_id, limit=10000)
    subs = svc.repo("tenant_subscriptions").list(tenant_id=current.tenant_id, limit=10000)
    active_subs = [s for s in subs if s.get("data", {}).get("status") == "active"]
    conversion_rate = round(len(active_subs) / max(len(proposals), 1) * 100, 2)
    return {
        "total_events": len(events),
        "total_proposals": len(proposals),
        "active_subscriptions": len(active_subs),
        "proposal_to_paid_conversion_pct": conversion_rate,
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.get("/subscription-lifecycle")
async def subscription_lifecycle(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    subs = svc.repo("tenant_subscriptions").list(tenant_id=current.tenant_id, limit=10000)
    statuses: dict[str, int] = {}
    for s in subs:
        status = s.get("data", {}).get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1
    return {"lifecycle": statuses, "total": len(subs), "as_of": datetime.now(UTC).isoformat()}


@router.post("/trial-activate")
async def trial_activate(
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    record = await svc.create(
        table="tenant_subscriptions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "tenant_id": body.get("tenant_id"),
            "plan": "trial",
            "status": "trial",
            "trial_ends_at": body.get("trial_ends_at"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.get("/revenue-pipeline")
async def revenue_pipeline(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    proposals = svc.repo("proposals").list(tenant_id=current.tenant_id, limit=10000)
    subs = svc.repo("tenant_subscriptions").list(tenant_id=current.tenant_id, limit=10000)
    pending_value = len([p for p in proposals if p.get("data", {}).get("status") == "pending"]) * 89900
    active_mrr = sum(int(s.get("data", {}).get("monthly_amount_cents", 0)) for s in subs if s.get("data", {}).get("status") == "active")
    return {
        "pending_pipeline_cents": pending_value,
        "active_mrr_cents": active_mrr,
        "pipeline_to_mrr_ratio": round(pending_value / max(active_mrr, 1), 2),
        "as_of": datetime.now(UTC).isoformat(),
    }
