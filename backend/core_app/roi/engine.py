import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"

@dataclass(frozen=True)
class FeeScheduleRow:
    service_type: str   # EMS|Fire|HEMS (HEMS treated as air medical placeholder)
    level: str          # BLS|ALS|CCT|HEMS
    base_rate: float    # USD
    mileage_rate: float # USD per mile


def _load_fee_schedule() -> list[FeeScheduleRow]:
    path = DATA_DIR / "medicare_fee_schedule_sample.csv"
    rows: list[FeeScheduleRow] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(FeeScheduleRow(
                service_type=r["service_type"],
                level=r["level"],
                base_rate=float(r["base_rate"]),
                mileage_rate=float(r["mileage_rate"]),
            ))
    return rows


_FEE = _load_fee_schedule()

def _rural_multiplier(zip_code: str) -> float:
    # Deterministic proxy. Replace with real RUCA/Rural-Urban datasets in production.
    # Simple rule: ZIPs starting with '5' get modest rural weight; else urban baseline.
    if zip_code.startswith("5"):
        return 1.06
    return 1.00


def compute_roi(inputs: dict[str, Any]) -> dict[str, Any]:
    zip_code = inputs["zip_code"]
    call_volume = int(inputs["annual_call_volume"])
    service_type = inputs["service_type"]
    billing_pct = float(inputs["current_billing_percent"]) / 100.0

    payer_mix: dict[str, float] = inputs.get("payer_mix", {}) or {"medicare": 0.4, "medicaid": 0.2, "commercial": 0.4}
    level_mix: dict[str, float] = inputs.get("level_mix", {}) or {"BLS": 0.5, "ALS": 0.5}

    rural_mult = _rural_multiplier(zip_code)

    def estimate_reimbursement(level: str) -> float:
        row = next((x for x in _FEE if x.service_type == service_type and x.level == level), None)
        if row is None:
            row = next((x for x in _FEE if x.service_type == "EMS" and x.level == level), None)
        base = row.base_rate if row else 400.0
        mileage = row.mileage_rate if row else 12.0
        # distance modeling (proxy): 10 miles baseline with rural multiplier
        return (base + mileage * 10.0) * rural_mult

    gross_current = 0.0
    for level, frac in level_mix.items():
        gross_current += call_volume * float(frac) * estimate_reimbursement(level)

    # payer mix proxy adjustment
    payer_adj = (
        payer_mix.get("medicare", 0.0) * 1.0
        + payer_mix.get("medicaid", 0.0) * 0.75
        + payer_mix.get("commercial", 0.0) * 1.25
        + payer_mix.get("self_pay", 0.0) * 0.35
    )
    gross_current *= payer_adj if payer_adj > 0 else 1.0

    pct_cost = gross_current * billing_pct
    retained_current = gross_current - pct_cost

    # Fusion uplift model (deterministic)
    denial_rate = float(inputs.get("denial_rate_estimate") or 0.12)
    days_in_ar = int(inputs.get("days_in_ar") or 45)
    collection_eff = float(inputs.get("collection_efficiency") or 0.92)

    denial_uplift = max(0.0, min(0.07, denial_rate * 0.35))  # reduce denials by 35% capped
    ar_uplift = max(0.0, min(0.05, (days_in_ar - 35) / 400.0))
    ai_uplift = 0.03 if "Advanced Billing AI" in (inputs.get("selected_modules") or []) else 0.015

    fusion_gross = gross_current * (1.0 + denial_uplift + ar_uplift + ai_uplift) * collection_eff

    # Subscription proxy (deterministic tier pricing)
    base_sub = 499.0
    per_call = 1.25
    module_cost = 0.0
    for m in inputs.get("selected_modules", []):
        module_cost += 99.0
    fusion_cost = 12 * (base_sub + module_cost) + call_volume * per_call

    retained_fusion = fusion_gross - fusion_cost
    delta_annual = retained_fusion - retained_current

    outputs = {
        "inputs_normalized": {
            "zip_code": zip_code,
            "annual_call_volume": call_volume,
            "service_type": service_type,
            "current_billing_percent": billing_pct,
            "payer_mix": payer_mix,
            "level_mix": level_mix,
            "selected_modules": inputs.get("selected_modules", []),
        },
        "current_model": {
            "estimated_gross_revenue": round(gross_current, 2),
            "percentage_billing_cost": round(pct_cost, 2),
            "retained_revenue": round(retained_current, 2),
        },
        "fusion_model": {
            "estimated_gross_revenue": round(fusion_gross, 2),
            "subscription_and_module_cost": round(fusion_cost, 2),
            "retained_revenue": round(retained_fusion, 2),
        },
        "delta": {
            "annual_retained_revenue_delta": round(delta_annual, 2),
            "monthly_retained_revenue_delta": round(delta_annual / 12.0, 2),
            "breakeven_months": 1 if delta_annual > 0 else None,
            "projection_3y": round(delta_annual * 3, 2),
            "projection_5y": round(delta_annual * 5, 2),
        },
    }
    return outputs


def hash_outputs(outputs: dict[str, Any]) -> str:
    canonical = str(outputs).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
