from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SchedulingTier:
    code: str
    label: str
    monthly_cents: int
    lookup_key: str


@dataclass(frozen=True)
class BillingTier:
    code: str
    label: str
    base_monthly_cents: int
    per_claim_cents: int
    base_lookup_key: str
    per_claim_lookup_key: str


@dataclass(frozen=True)
class Plan:
    code: str
    label: str
    desc: str
    contact_sales: bool
    color: str


@dataclass(frozen=True)
class Addon:
    code: str
    label: str
    monthly_cents: int
    gov_only: bool
    uses_billing_tier: bool
    lookup_key: str


@dataclass
class QuoteResult:
    plan_code: str
    tier_code: str | None
    billing_tier_code: str | None
    addon_codes: list[str]
    base_monthly_cents: int
    addon_monthly_cents: int
    total_monthly_cents: int
    requires_quote: bool
    stripe_line_items: list[dict] = field(default_factory=list)


SCHEDULING_TIERS: dict[str, SchedulingTier] = {
    "S1": SchedulingTier(
        code="S1", label="1–25 active users", monthly_cents=19900,
        lookup_key="SCHEDULING_ONLY_S1_V1_MONTHLY",
    ),
    "S2": SchedulingTier(
        code="S2", label="26–75 active users", monthly_cents=39900,
        lookup_key="SCHEDULING_ONLY_S2_V1_MONTHLY",
    ),
    "S3": SchedulingTier(
        code="S3", label="76–150 active users", monthly_cents=69900,
        lookup_key="SCHEDULING_ONLY_S3_V1_MONTHLY",
    ),
}

BILLING_TIERS: dict[str, BillingTier] = {
    "B1": BillingTier(
        code="B1", label="0–150 claims/mo",
        base_monthly_cents=39900, per_claim_cents=600,
        base_lookup_key="BILLING_AUTOMATION_B1_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B1_PER_CLAIM_V1",
    ),
    "B2": BillingTier(
        code="B2", label="151–400 claims/mo",
        base_monthly_cents=59900, per_claim_cents=500,
        base_lookup_key="BILLING_AUTOMATION_B2_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B2_PER_CLAIM_V1",
    ),
    "B3": BillingTier(
        code="B3", label="401–1,000 claims/mo",
        base_monthly_cents=99900, per_claim_cents=400,
        base_lookup_key="BILLING_AUTOMATION_B3_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B3_PER_CLAIM_V1",
    ),
    "B4": BillingTier(
        code="B4", label="1,001+ claims/mo",
        base_monthly_cents=149900, per_claim_cents=325,
        base_lookup_key="BILLING_AUTOMATION_B4_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B4_PER_CLAIM_V1",
    ),
}

PLANS: dict[str, Plan] = {
    "SCHEDULING_ONLY": Plan(
        code="SCHEDULING_ONLY", label="Scheduling Only",
        desc="Calendar, shifts, crew, bids, scheduling PWA",
        contact_sales=False, color="var(--color-status-info)",
    ),
    "OPS_CORE": Plan(
        code="OPS_CORE", label="Ops Core",
        desc="TransportLink + CAD + CrewLink + Scheduling",
        contact_sales=True, color="var(--q-green)",
    ),
    "CLINICAL_CORE": Plan(
        code="CLINICAL_CORE", label="Clinical Core",
        desc="ePCR + NEMSIS/WI validation + Scheduling",
        contact_sales=True, color="var(--color-system-compliance)",
    ),
    "FULL_STACK": Plan(
        code="FULL_STACK", label="Full Stack",
        desc="Everything — Ops + Clinical + HEMS + NERIS",
        contact_sales=True, color="var(--q-orange)",
    ),
}

ADDONS: dict[str, Addon] = {
    "CCT_TRANSPORT_OPS": Addon(
        code="CCT_TRANSPORT_OPS", label="CCT / Transport Ops",
        monthly_cents=39900, gov_only=False, uses_billing_tier=False,
        lookup_key="CCT_TRANSPORT_OPS_V1_MONTHLY",
    ),
    "HEMS_OPS": Addon(
        code="HEMS_OPS", label="HEMS Ops (rotor + fixed-wing)",
        monthly_cents=75000, gov_only=False, uses_billing_tier=False,
        lookup_key="HEMS_OPS_V1_MONTHLY",
    ),
    "BILLING_AUTOMATION": Addon(
        code="BILLING_AUTOMATION", label="Billing Automation",
        monthly_cents=0, gov_only=False, uses_billing_tier=True,
        lookup_key="",
    ),
    "TRIP_PACK": Addon(
        code="TRIP_PACK", label="Wisconsin TRIP Pack (gov agencies only)",
        monthly_cents=19900, gov_only=True, uses_billing_tier=False,
        lookup_key="TRIP_PACK_V1_MONTHLY",
    ),
}


def calculate_quote(
    plan_code: str,
    tier_code: str | None = None,
    billing_tier_code: str | None = None,
    addon_codes: list[str] | None = None,
) -> QuoteResult:
    if plan_code not in PLANS:
        raise ValueError(f"Unknown plan_code: {plan_code!r}")

    plan = PLANS[plan_code]
    addon_codes = list(addon_codes or [])

    for ac in addon_codes:
        if ac not in ADDONS:
            raise ValueError(f"Unknown addon_code: {ac!r}")

    if plan.contact_sales:
        return QuoteResult(
            plan_code=plan_code,
            tier_code=tier_code,
            billing_tier_code=billing_tier_code,
            addon_codes=addon_codes,
            base_monthly_cents=0,
            addon_monthly_cents=0,
            total_monthly_cents=0,
            requires_quote=True,
            stripe_line_items=[],
        )

    stripe_line_items: list[dict] = []

    if plan_code == "SCHEDULING_ONLY":
        if not tier_code:
            raise ValueError("tier_code is required for SCHEDULING_ONLY plan")
        if tier_code not in SCHEDULING_TIERS:
            raise ValueError(f"Unknown tier_code: {tier_code!r}")
        tier = SCHEDULING_TIERS[tier_code]
        base_monthly_cents = tier.monthly_cents
        stripe_line_items.append({"lookup_key": tier.lookup_key, "quantity": 1, "metered": False})
    else:
        base_monthly_cents = 0

    addon_monthly_cents = 0
    for ac in addon_codes:
        addon = ADDONS[ac]
        if addon.uses_billing_tier:
            if not billing_tier_code:
                raise ValueError(f"billing_tier_code is required for addon {ac!r}")
            if billing_tier_code not in BILLING_TIERS:
                raise ValueError(f"Unknown billing_tier_code: {billing_tier_code!r}")
            bt = BILLING_TIERS[billing_tier_code]
            addon_monthly_cents += bt.base_monthly_cents
            stripe_line_items.append({"lookup_key": bt.base_lookup_key, "quantity": 1, "metered": False})
            stripe_line_items.append({"lookup_key": bt.per_claim_lookup_key, "metered": True})
        else:
            addon_monthly_cents += addon.monthly_cents
            if addon.lookup_key:
                stripe_line_items.append({"lookup_key": addon.lookup_key, "quantity": 1, "metered": False})

    return QuoteResult(
        plan_code=plan_code,
        tier_code=tier_code,
        billing_tier_code=billing_tier_code,
        addon_codes=addon_codes,
        base_monthly_cents=base_monthly_cents,
        addon_monthly_cents=addon_monthly_cents,
        total_monthly_cents=base_monthly_cents + addon_monthly_cents,
        requires_quote=False,
        stripe_line_items=stripe_line_items,
    )


def get_catalog() -> dict:
    def _fmt_cents(cents: int) -> str:
        dollars = cents / 100
        if dollars == int(dollars):
            return f"${int(dollars)}"
        return f"${dollars:.2f}"

    return {
        "plans": [
            {
                "code": p.code,
                "label": p.label,
                "desc": p.desc,
                "contact_sales": p.contact_sales,
                "color": p.color,
                "price_display": "Contact us" if p.contact_sales else (
                    f"from {_fmt_cents(min(t.monthly_cents for t in SCHEDULING_TIERS.values()))}/mo"
                    if p.code == "SCHEDULING_ONLY" else ""
                ),
            }
            for p in PLANS.values()
        ],
        "scheduling_tiers": [
            {
                "code": t.code,
                "label": t.label,
                "monthly_cents": t.monthly_cents,
                "price_display": f"{_fmt_cents(t.monthly_cents)}/mo",
            }
            for t in SCHEDULING_TIERS.values()
        ],
        "billing_tiers": [
            {
                "code": t.code,
                "label": t.label,
                "base_monthly_cents": t.base_monthly_cents,
                "per_claim_cents": t.per_claim_cents,
                "base_display": f"{_fmt_cents(t.base_monthly_cents)}/mo",
                "per_claim_display": f"+{_fmt_cents(t.per_claim_cents)}/claim",
            }
            for t in BILLING_TIERS.values()
        ],
        "addons": [
            {
                "code": a.code,
                "label": a.label,
                "monthly_cents": a.monthly_cents,
                "gov_only": a.gov_only,
                "uses_billing_tier": a.uses_billing_tier,
                "price_display": (
                    "see billing_tiers" if a.uses_billing_tier
                    else f"+{_fmt_cents(a.monthly_cents)}/mo"
                ),
            }
            for a in ADDONS.values()
        ],
    }
