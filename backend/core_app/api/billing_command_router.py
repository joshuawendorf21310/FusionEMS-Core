from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.billing.ar_aging import compute_revenue_forecast

router = APIRouter(prefix="/api/v1/billing-command", tags=["Billing Command Center"])


class DenialPredictionRequest(BaseModel):
    claim_id: uuid.UUID
    payer_id: str = ""
    procedure_codes: list[str] = Field(default_factory=list)
    diagnosis_codes: list[str] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)


class BatchResubmitRequest(BaseModel):
    claim_ids: list[uuid.UUID]
    resubmit_reason: str = "initial_denial"


class ContractSimRequest(BaseModel):
    payer_id: str
    proposed_rate_cents: int
    current_rate_cents: int
    annual_volume: int


class BillingAlertThresholdRequest(BaseModel):
    metric: str
    threshold_value: float
    alert_type: str = "email"
    recipients: list[str] = Field(default_factory=list)


class AppealDraftRequest(BaseModel):
    claim_id: uuid.UUID
    denial_reason: str
    supporting_context: str = ""


class PayerFollowUpRequest(BaseModel):
    payer_id: str
    claim_ids: list[uuid.UUID]
    follow_up_method: str = "phone"


@router.get("/dashboard")
async def revenue_dashboard(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    total = len(claims)
    paid = sum(1 for c in claims if c.get("data", {}).get("status") == "paid")
    denied = sum(1 for c in claims if c.get("data", {}).get("status") == "denied")
    pending = sum(1 for c in claims if c.get("data", {}).get("status") in ("submitted", "pending"))
    revenue_cents = sum(int(c.get("data", {}).get("paid_amount_cents", 0)) for c in claims)
    clean_claim_rate = round((paid / total * 100) if total > 0 else 0, 2)
    denial_rate = round((denied / total * 100) if total > 0 else 0, 2)
    return {
        "total_claims": total,
        "paid_claims": paid,
        "denied_claims": denied,
        "pending_claims": pending,
        "revenue_cents": revenue_cents,
        "clean_claim_rate_pct": clean_claim_rate,
        "denial_rate_pct": denial_rate,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/denial-heatmap")
async def denial_heatmap(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    denials = svc.repo("denials").list(tenant_id=current.tenant_id, limit=10000)
    heatmap: dict[str, int] = {}
    for d in denials:
        reason = d.get("data", {}).get("reason_code", "UNKNOWN")
        heatmap[reason] = heatmap.get(reason, 0) + 1
    sorted_heatmap = sorted(heatmap.items(), key=lambda x: x[1], reverse=True)
    return {
        "heatmap": [{"reason_code": k, "count": v} for k, v in sorted_heatmap],
        "total_denials": len(denials),
        "top_reason": sorted_heatmap[0][0] if sorted_heatmap else None,
    }


@router.get("/payer-performance")
async def payer_performance(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    payer_stats: dict[str, dict] = {}
    for c in claims:
        d = c.get("data", {})
        payer = d.get("payer_name", "UNKNOWN")
        if payer not in payer_stats:
            payer_stats[payer] = {"total": 0, "paid": 0, "denied": 0, "revenue_cents": 0, "days_to_payment": []}
        payer_stats[payer]["total"] += 1
        status = d.get("status", "")
        if status == "paid":
            payer_stats[payer]["paid"] += 1
            payer_stats[payer]["revenue_cents"] += int(d.get("paid_amount_cents", 0))
        elif status == "denied":
            payer_stats[payer]["denied"] += 1
        dtp = d.get("days_to_payment")
        if dtp:
            payer_stats[payer]["days_to_payment"].append(int(dtp))
    results = []
    for payer, stats in payer_stats.items():
        avg_dtp = round(sum(stats["days_to_payment"]) / len(stats["days_to_payment"]), 1) if stats["days_to_payment"] else None
        clean_rate = round(stats["paid"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
        results.append({
            "payer": payer,
            "total_claims": stats["total"],
            "paid": stats["paid"],
            "denied": stats["denied"],
            "revenue_cents": stats["revenue_cents"],
            "clean_claim_rate_pct": clean_rate,
            "avg_days_to_payment": avg_dtp,
        })
    results.sort(key=lambda x: x["revenue_cents"], reverse=True)
    return {"payers": results}


@router.get("/revenue-leakage")
async def revenue_leakage(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    leakage_items = []
    total_leakage_cents = 0
    for c in claims:
        d = c.get("data", {})
        if d.get("status") == "denied" and not d.get("appealed"):
            amount = int(d.get("billed_amount_cents", 0))
            total_leakage_cents += amount
            leakage_items.append({
                "claim_id": c["id"],
                "payer": d.get("payer_name"),
                "amount_cents": amount,
                "denial_reason": d.get("denial_reason"),
                "leakage_type": "unappealed_denial",
            })
        if d.get("underbilled"):
            delta = int(d.get("underbilled_delta_cents", 0))
            total_leakage_cents += delta
            leakage_items.append({
                "claim_id": c["id"],
                "amount_cents": delta,
                "leakage_type": "underbilling",
            })
    return {
        "total_leakage_cents": total_leakage_cents,
        "leakage_items": leakage_items[:50],
        "item_count": len(leakage_items),
    }


@router.get("/modifier-impact")
async def modifier_impact(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    modifier_stats: dict[str, dict] = {}
    for c in claims:
        d = c.get("data", {})
        for mod in d.get("modifiers", []):
            if mod not in modifier_stats:
                modifier_stats[mod] = {"total": 0, "paid": 0, "denied": 0, "revenue_cents": 0}
            modifier_stats[mod]["total"] += 1
            if d.get("status") == "paid":
                modifier_stats[mod]["paid"] += 1
                modifier_stats[mod]["revenue_cents"] += int(d.get("paid_amount_cents", 0))
            elif d.get("status") == "denied":
                modifier_stats[mod]["denied"] += 1
    return {"modifiers": [{"modifier": k, **v} for k, v in modifier_stats.items()]}


@router.get("/claim-lifecycle/{claim_id}")
async def claim_lifecycle(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claim = svc.repo("claims").get(tenant_id=current.tenant_id, record_id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="claim_not_found")
    all_events = svc.repo("claim_events").list(tenant_id=current.tenant_id, limit=10000)
    events = [e for e in all_events if e.get("data", {}).get("claim_id") == str(claim_id)]
    events.sort(key=lambda e: e.get("created_at", ""))
    return {"claim": claim, "lifecycle_events": events}


@router.post("/denial-predictor")
async def predict_denial(
    body: DenialPredictionRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    denials = svc.repo("denials").list(tenant_id=current.tenant_id, limit=10000)
    payer_denials = [d for d in denials if d.get("data", {}).get("payer_id") == body.payer_id]
    total_by_payer = len(payer_denials)
    risk_score = min(round(total_by_payer / max(1, len(denials)) * 100, 2), 100)
    risk_flags = []
    if risk_score > 30:
        risk_flags.append("high_payer_denial_rate")
    if len(body.modifiers) == 0:
        risk_flags.append("no_modifiers_attached")
    prediction = await svc.create(
        table="denial_predictions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "claim_id": str(body.claim_id),
            "payer_id": body.payer_id,
            "risk_score": risk_score,
            "risk_flags": risk_flags,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return prediction


@router.get("/appeal-success")
async def appeal_success_tracker(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    appeals = svc.repo("appeals").list(tenant_id=current.tenant_id, limit=10000)
    total = len(appeals)
    successful = sum(1 for a in appeals if a.get("data", {}).get("status") in ("approved", "paid"))
    success_rate = round(successful / total * 100, 2) if total > 0 else 0
    return {
        "total_appeals": total,
        "successful": successful,
        "success_rate_pct": success_rate,
    }


@router.get("/billing-kpis")
async def billing_kpis(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    total = len(claims)
    paid = sum(1 for c in claims if c.get("data", {}).get("status") == "paid")
    denied = sum(1 for c in claims if c.get("data", {}).get("status") == "denied")
    revenue = sum(int(c.get("data", {}).get("paid_amount_cents", 0)) for c in claims if c.get("data", {}).get("status") == "paid")
    dtp_values = [int(c.get("data", {}).get("days_to_payment", 0)) for c in claims if c.get("data", {}).get("days_to_payment")]
    avg_dtp = round(sum(dtp_values) / len(dtp_values), 1) if dtp_values else None
    return {
        "total_claims": total,
        "clean_claim_rate": round(paid / total * 100, 2) if total else 0,
        "denial_rate": round(denied / total * 100, 2) if total else 0,
        "total_revenue_cents": revenue,
        "avg_days_to_payment": avg_dtp,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/batch-resubmit")
async def batch_resubmit(
    body: BatchResubmitRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    results = []
    for claim_id in body.claim_ids:
        claim = svc.repo("claims").get(tenant_id=current.tenant_id, record_id=claim_id)
        if not claim:
            results.append({"claim_id": str(claim_id), "status": "not_found"})
            continue
        updated = await svc.update(
            table="claims",
            tenant_id=current.tenant_id,
            record_id=claim["id"],
            actor_user_id=current.user_id,
            expected_version=claim.get("version", 1),
            patch={"status": "resubmitted", "resubmit_reason": body.resubmit_reason, "resubmitted_at": datetime.now(timezone.utc).isoformat()},
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        results.append({"claim_id": str(claim_id), "status": "resubmitted"})
    return {"results": results, "total": len(results)}


@router.get("/fraud-anomaly")
async def fraud_anomaly(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    anomalies = []
    patient_counts: dict[str, int] = {}
    for c in claims:
        d = c.get("data", {})
        pid = d.get("patient_id", "unknown")
        patient_counts[pid] = patient_counts.get(pid, 0) + 1
    for pid, count in patient_counts.items():
        if count > 10:
            anomalies.append({"type": "duplicate_billing_risk", "patient_id": pid, "claim_count": count})
    return {"anomalies": anomalies, "total_anomalies": len(anomalies)}


@router.get("/duplicate-detection")
async def duplicate_detection(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    seen: dict[str, list] = {}
    for c in claims:
        d = c.get("data", {})
        key = f"{d.get('patient_id')}_{d.get('dos')}_{d.get('procedure_code')}"
        if key not in seen:
            seen[key] = []
        seen[key].append(c["id"])
    duplicates = [{
        "key": k,
        "claim_ids": v,
        "count": len(v),
    } for k, v in seen.items() if len(v) > 1]
    return {"duplicates": duplicates, "total_duplicate_groups": len(duplicates)}


@router.post("/contract-simulation")
async def contract_simulation(
    body: ContractSimRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    current_annual = body.current_rate_cents * body.annual_volume
    proposed_annual = body.proposed_rate_cents * body.annual_volume
    delta = proposed_annual - current_annual
    return {
        "payer_id": body.payer_id,
        "current_annual_revenue_cents": current_annual,
        "proposed_annual_revenue_cents": proposed_annual,
        "delta_cents": delta,
        "delta_pct": round(delta / max(current_annual, 1) * 100, 2),
        "recommendation": "accept" if delta > 0 else "negotiate",
    }


@router.get("/stripe-reconciliation")
async def stripe_reconciliation(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    subscriptions = svc.repo("tenant_subscriptions").list(tenant_id=current.tenant_id, limit=10000)
    active = [s for s in subscriptions if s.get("data", {}).get("status") == "active"]
    past_due = [s for s in subscriptions if s.get("data", {}).get("status") == "past_due"]
    mrr = sum(int(s.get("data", {}).get("monthly_amount_cents", 0)) for s in active)
    return {
        "active_subscriptions": len(active),
        "past_due_subscriptions": len(past_due),
        "mrr_cents": mrr,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/churn-risk")
async def churn_risk(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    subscriptions = svc.repo("tenant_subscriptions").list(tenant_id=current.tenant_id, limit=10000)
    at_risk = []
    for s in subscriptions:
        d = s.get("data", {})
        if d.get("status") in ("past_due", "canceled", "paused"):
            at_risk.append({
                "subscription_id": s["id"],
                "tenant_id": d.get("tenant_id"),
                "status": d.get("status"),
                "monthly_amount_cents": int(d.get("monthly_amount_cents", 0)),
            })
    return {"at_risk_subscriptions": at_risk, "count": len(at_risk)}


@router.post("/appeal-draft")
async def ai_appeal_draft(
    body: AppealDraftRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claim = svc.repo("claims").get(tenant_id=current.tenant_id, record_id=body.claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="claim_not_found")
    d = claim.get("data", {})
    draft = (
        f"FORMAL APPEAL\n"
        f"Claim ID: {body.claim_id}\n"
        f"Patient: {d.get('patient_name', 'N/A')}\n"
        f"Date of Service: {d.get('dos', 'N/A')}\n"
        f"Payer: {d.get('payer_name', 'N/A')}\n\n"
        f"Denial Reason: {body.denial_reason}\n\n"
        f"We respectfully appeal this denial based on documented medical necessity and applicable coverage guidelines. "
        f"{body.supporting_context}\n\n"
        f"Supporting documentation is attached herewith.\n\nRespectfully,\nFusionEMS Billing Team\n"
    )
    record = await svc.create(
        table="appeal_drafts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"claim_id": str(body.claim_id), "draft": draft, "status": "draft"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"draft": record, "letter": draft}


@router.get("/billing-alerts")
async def billing_alerts(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    alerts = []
    denied = [c for c in claims if c.get("data", {}).get("status") == "denied"]
    if len(denied) > 50:
        alerts.append({"type": "high_denial_volume", "count": len(denied), "severity": "high"})
    overdue_links = svc.repo("patient_payment_links").list(tenant_id=current.tenant_id, limit=1000)
    overdue = [l for l in overdue_links if l.get("data", {}).get("status") == "overdue"]
    if overdue:
        alerts.append({"type": "overdue_payments", "count": len(overdue), "severity": "medium"})
    return {"alerts": alerts, "total": len(alerts), "as_of": datetime.now(timezone.utc).isoformat()}


@router.post("/alert-thresholds")
async def set_alert_threshold(
    body: BillingAlertThresholdRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    record = await svc.create(
        table="billing_alert_thresholds",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=body.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.get("/revenue-by-service-level")
async def revenue_by_service_level(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    service_stats: dict[str, dict] = {}
    for c in claims:
        d = c.get("data", {})
        level = d.get("service_level", "UNKNOWN")
        if level not in service_stats:
            service_stats[level] = {"total": 0, "revenue_cents": 0}
        service_stats[level]["total"] += 1
        service_stats[level]["revenue_cents"] += int(d.get("paid_amount_cents", 0))
    return {"service_levels": [{"level": k, **v} for k, v in service_stats.items()]}


@router.get("/payer-mix")
async def payer_mix(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    mix: dict[str, int] = {}
    for c in claims:
        payer = c.get("data", {}).get("payer_category", "unknown")
        mix[payer] = mix.get(payer, 0) + 1
    total = sum(mix.values())
    return {
        "payer_mix": [{"category": k, "count": v, "pct": round(v / total * 100, 2) if total else 0} for k, v in mix.items()],
        "total_claims": total,
    }


@router.get("/ar-concentration-risk")
async def ar_concentration_risk(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    open_claims = [c for c in claims if c.get("data", {}).get("status") in ("submitted", "pending", "denied")]
    payer_ar: dict[str, int] = {}
    total_ar = 0
    for c in open_claims:
        d = c.get("data", {})
        payer = d.get("payer_name", "UNKNOWN")
        amount = int(d.get("billed_amount_cents", 0))
        payer_ar[payer] = payer_ar.get(payer, 0) + amount
        total_ar += amount
    concentration = []
    for payer, amount in payer_ar.items():
        pct = round(amount / total_ar * 100, 2) if total_ar else 0
        risk = "high" if pct > 40 else ("medium" if pct > 20 else "low")
        concentration.append({"payer": payer, "ar_cents": amount, "pct": pct, "risk": risk})
    concentration.sort(key=lambda x: x["ar_cents"], reverse=True)
    return {"concentration": concentration, "total_ar_cents": total_ar}


@router.get("/claim-throughput")
async def claim_throughput(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    daily_counts: dict[str, int] = {}
    for c in claims:
        created = c.get("created_at", "")[:10]
        daily_counts[created] = daily_counts.get(created, 0) + 1
    sorted_days = sorted(daily_counts.items())
    return {
        "throughput_by_day": [{"date": d, "count": c} for d, c in sorted_days],
        "avg_daily": round(sum(daily_counts.values()) / max(len(daily_counts), 1), 1),
    }


@router.get("/revenue-trend")
async def revenue_trend(
    months: int = 6,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    forecast = compute_revenue_forecast(db, current.tenant_id, months=months)
    return forecast


@router.get("/billing-health")
async def billing_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    total = len(claims)
    paid = sum(1 for c in claims if c.get("data", {}).get("status") == "paid")
    clean_rate = round(paid / total * 100, 2) if total else 0
    score = min(100, clean_rate)
    health_status = "excellent" if score >= 90 else ("good" if score >= 75 else ("fair" if score >= 60 else "poor"))
    return {
        "health_score": score,
        "status": health_status,
        "clean_claim_rate_pct": clean_rate,
        "total_claims": total,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/tenant-billing-ranking")
async def tenant_billing_ranking(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())
    tenants = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=10000)
    return {"tenants": tenants[:20], "as_of": datetime.now(timezone.utc).isoformat()}


@router.post("/payer-follow-up")
async def payer_follow_up(
    body: PayerFollowUpRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    follow_ups = []
    for claim_id in body.claim_ids:
        record = await svc.create(
            table="payer_follow_ups",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "claim_id": str(claim_id),
                "payer_id": body.payer_id,
                "method": body.follow_up_method,
                "status": "scheduled",
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        follow_ups.append(record)
    return {"follow_ups": follow_ups, "total": len(follow_ups)}


@router.get("/executive-summary")
async def executive_summary(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    claims = svc.repo("claims").list(tenant_id=current.tenant_id, limit=10000)
    total = len(claims)
    revenue = sum(int(c.get("data", {}).get("paid_amount_cents", 0)) for c in claims if c.get("data", {}).get("status") == "paid")
    subscriptions = svc.repo("tenant_subscriptions").list(tenant_id=current.tenant_id, limit=1000)
    mrr = sum(int(s.get("data", {}).get("monthly_amount_cents", 0)) for s in subscriptions if s.get("data", {}).get("status") == "active")
    return {
        "total_claims": total,
        "total_revenue_cents": revenue,
        "mrr_cents": mrr,
        "arr_cents": mrr * 12,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
