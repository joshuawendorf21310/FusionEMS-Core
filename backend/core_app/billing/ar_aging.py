from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher


@dataclass
class AgingBucket:
    label: str
    min_days: int
    max_days: int | None
    count: int = 0
    total_cents: int = 0
    claim_ids: list[str] = field(default_factory=list)


@dataclass
class ArAgingReport:
    tenant_id: str
    as_of_date: str
    buckets: list[AgingBucket]
    total_ar_cents: int
    total_claims: int
    avg_days_in_ar: float
    payer_breakdown: dict[str, dict[str, Any]]


AGING_BUCKETS = [
    AgingBucket("0-30", 0, 30),
    AgingBucket("31-60", 31, 60),
    AgingBucket("61-90", 61, 90),
    AgingBucket("91-120", 91, 120),
    AgingBucket("120+", 121, None),
]


def compute_ar_aging(
    db: Session, tenant_id: uuid.UUID, svc: DominationService | None = None
) -> ArAgingReport:
    if svc is None:
        svc = DominationService(db, get_event_publisher())
    today = date.today()

    buckets = [copy.deepcopy(b) for b in AGING_BUCKETS]

    claims = svc.repo("billing_cases").list(tenant_id=tenant_id, limit=50000)

    payer_breakdown: dict[str, dict[str, Any]] = {}
    total_ar_cents = 0
    total_claims = 0
    days_list: list[int] = []

    for claim in claims:
        data = claim.get("data", {})
        status = data.get("status", "")
        if status in ("paid", "voided", "written_off"):
            continue

        billed_date_raw = (
            data.get("billed_date") or data.get("service_date") or claim.get("created_at")
        )
        if not billed_date_raw:
            continue

        try:
            if isinstance(billed_date_raw, str):
                billed_date = datetime.fromisoformat(billed_date_raw.replace("Z", "+00:00")).date()
            else:
                billed_date = billed_date_raw
        except Exception:
            continue

        days_out = (today - billed_date).days
        amount_cents = int(data.get("balance_cents", data.get("billed_cents", 0)) or 0)

        for bucket in buckets:
            if bucket.min_days <= days_out and (
                bucket.max_days is None or days_out <= bucket.max_days
            ):
                bucket.count += 1
                bucket.total_cents += amount_cents
                bucket.claim_ids.append(claim.get("id", ""))
                break

        payer = data.get("primary_payer", "Unknown")
        if payer not in payer_breakdown:
            payer_breakdown[payer] = {"count": 0, "total_cents": 0, "avg_days": 0, "days_sum": 0}
        payer_breakdown[payer]["count"] += 1
        payer_breakdown[payer]["total_cents"] += amount_cents
        payer_breakdown[payer]["days_sum"] += days_out

        total_ar_cents += amount_cents
        total_claims += 1
        days_list.append(days_out)

    for _, data_p in payer_breakdown.items():
        if data_p["count"] > 0:
            data_p["avg_days"] = round(data_p["days_sum"] / data_p["count"], 1)

    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else 0.0

    return ArAgingReport(
        tenant_id=str(tenant_id),
        as_of_date=today.isoformat(),
        buckets=buckets,
        total_ar_cents=total_ar_cents,
        total_claims=total_claims,
        avg_days_in_ar=avg_days,
        payer_breakdown=payer_breakdown,
    )


def compute_revenue_forecast(
    db: Session, tenant_id: uuid.UUID, months: int = 3, svc: DominationService | None = None
) -> dict[str, Any]:
    if svc is None:
        svc = DominationService(db, get_event_publisher())

    payments = svc.repo("payments").list(tenant_id=tenant_id, limit=50000)

    monthly_revenue: dict[str, int] = {}
    for payment in payments:
        data = payment.get("data", {})
        paid_at = data.get("paid_at") or payment.get("created_at")
        amount = int(data.get("amount_cents", 0) or 0)
        if not paid_at:
            continue
        try:
            month_key = paid_at[:7]
            monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + amount
        except Exception:
            continue

    sorted_months = sorted(monthly_revenue.keys())
    recent_months = sorted_months[-6:] if len(sorted_months) >= 6 else sorted_months
    avg_monthly = (
        int(sum(monthly_revenue[m] for m in recent_months) / len(recent_months))
        if recent_months
        else 0
    )

    today = date.today()
    forecast = []
    for i in range(1, months + 1):
        future = today + relativedelta(months=i)
        forecast.append(
            {
                "month": future.strftime("%Y-%m"),
                "projected_cents": avg_monthly,
                "confidence": "low"
                if len(recent_months) < 3
                else "medium"
                if len(recent_months) < 6
                else "high",
            }
        )

    return {
        "historical_monthly": {m: monthly_revenue[m] for m in sorted_months[-12:]},
        "avg_monthly_cents": avg_monthly,
        "forecast": forecast,
        "months_of_data": len(sorted_months),
    }
