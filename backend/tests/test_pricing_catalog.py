from __future__ import annotations

import pytest

from core_app.pricing.catalog import (
    ADDONS,
    BILLING_TIERS,
    PLANS,
    SCHEDULING_TIERS,
    calculate_quote,
    get_catalog,
)


def test_calculate_quote_scheduling_only_s1():
    q = calculate_quote(plan_code="SCHEDULING_ONLY", tier_code="S1")
    assert q.requires_quote is False
    assert q.base_monthly_cents == 19900
    assert q.total_monthly_cents == 19900
    assert q.addon_monthly_cents == 0
    assert len(q.stripe_line_items) == 1
    assert q.stripe_line_items[0]["lookup_key"] == "SCHEDULING_ONLY_S1_V1_MONTHLY"


def test_calculate_quote_scheduling_only_all_tiers():
    expected = {"S1": 19900, "S2": 39900, "S3": 69900}
    for tier_code, cents in expected.items():
        q = calculate_quote(plan_code="SCHEDULING_ONLY", tier_code=tier_code)
        assert q.total_monthly_cents == cents, f"Tier {tier_code}: expected {cents}"


def test_calculate_quote_scheduling_only_missing_tier():
    with pytest.raises(ValueError, match="tier_code is required"):
        calculate_quote(plan_code="SCHEDULING_ONLY")


def test_calculate_quote_scheduling_only_unknown_tier():
    with pytest.raises(ValueError, match="Unknown tier_code"):
        calculate_quote(plan_code="SCHEDULING_ONLY", tier_code="S99")


def test_calculate_quote_unknown_plan():
    with pytest.raises(ValueError, match="Unknown plan_code"):
        calculate_quote(plan_code="DOES_NOT_EXIST")


def test_calculate_quote_contact_sales_plans():
    for plan_code in ("OPS_CORE", "CLINICAL_CORE", "FULL_STACK"):
        q = calculate_quote(plan_code=plan_code)
        assert q.requires_quote is True
        assert q.total_monthly_cents == 0
        assert q.stripe_line_items == []


def test_calculate_quote_billing_automation_requires_billing_tier():
    with pytest.raises(ValueError, match="billing_tier_code is required"):
        calculate_quote(
            plan_code="SCHEDULING_ONLY",
            tier_code="S1",
            addon_codes=["BILLING_AUTOMATION"],
        )


def test_calculate_quote_billing_automation_b1():
    q = calculate_quote(
        plan_code="SCHEDULING_ONLY",
        tier_code="S1",
        addon_codes=["BILLING_AUTOMATION"],
        billing_tier_code="B1",
    )
    assert q.requires_quote is False
    assert q.addon_monthly_cents == 39900
    assert q.total_monthly_cents == 19900 + 39900
    lookup_keys = [item["lookup_key"] for item in q.stripe_line_items]
    assert "BILLING_AUTOMATION_B1_BASE_V1_MONTHLY" in lookup_keys
    assert "BILLING_AUTOMATION_B1_PER_CLAIM_V1" in lookup_keys


def test_calculate_quote_addon_unknown():
    with pytest.raises(ValueError, match="Unknown addon_code"):
        calculate_quote(
            plan_code="SCHEDULING_ONLY",
            tier_code="S1",
            addon_codes=["NOT_A_REAL_ADDON"],
        )


def test_calculate_quote_cct_addon():
    q = calculate_quote(
        plan_code="SCHEDULING_ONLY",
        tier_code="S2",
        addon_codes=["CCT_TRANSPORT_OPS"],
    )
    assert q.addon_monthly_cents == 39900
    assert q.total_monthly_cents == 39900 + 39900


def test_get_catalog_structure():
    catalog = get_catalog()
    assert "plans" in catalog
    assert "scheduling_tiers" in catalog
    assert "billing_tiers" in catalog
    assert "addons" in catalog
    assert len(catalog["plans"]) == len(PLANS)
    assert len(catalog["scheduling_tiers"]) == len(SCHEDULING_TIERS)
    assert len(catalog["billing_tiers"]) == len(BILLING_TIERS)
    assert len(catalog["addons"]) == len(ADDONS)


def test_get_catalog_plan_fields():
    catalog = get_catalog()
    for plan in catalog["plans"]:
        assert "code" in plan
        assert "label" in plan
        assert "contact_sales" in plan
        assert "price_display" in plan


def test_get_catalog_scheduling_tier_price_display():
    catalog = get_catalog()
    tiers = {t["code"]: t for t in catalog["scheduling_tiers"]}
    assert tiers["S1"]["price_display"] == "$199/mo"
    assert tiers["S2"]["price_display"] == "$399/mo"
    assert tiers["S3"]["price_display"] == "$699/mo"
