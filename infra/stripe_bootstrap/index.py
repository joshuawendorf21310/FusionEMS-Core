"""
Stripe Bootstrap Lambda (CloudFormation custom resource).
Idempotently creates/updates Stripe Products and Prices using lookup_keys.
Reads pricing spec from environment or S3.
Stores Stripe IDs in SSM.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
import stripe

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
SSM_PREFIX = os.environ.get("SSM_PREFIX", "/quantumems/dev/stripe")
STAGE = os.environ.get("STAGE", "dev")

PRODUCTS = [
    {"key": "SCHEDULING_ONLY", "name": "QuantumEMS Scheduling Only"},
    {"key": "OPS_CORE", "name": "QuantumEMS Ops Core"},
    {"key": "CLINICAL_CORE", "name": "QuantumEMS Clinical Core"},
    {"key": "FULL_STACK", "name": "QuantumEMS Full Stack"},
    {"key": "BILLING_AUTOMATION_BASE", "name": "Billing Automation Base"},
    {"key": "CCT_TRANSPORT_OPS_ADDON", "name": "CCT / Transport Ops Add-on"},
    {"key": "HEMS_ADDON", "name": "HEMS Ops Add-on"},
    {"key": "TRIP_PACK_ADDON", "name": "Wisconsin TRIP Pack Add-on"},
]

PRICES = [
    {"lookup_key": "SCHEDULING_S1_MONTHLY", "product_key": "SCHEDULING_ONLY", "unit_amount": 19900, "nickname": "Scheduling 1-25 users"},
    {"lookup_key": "SCHEDULING_S2_MONTHLY", "product_key": "SCHEDULING_ONLY", "unit_amount": 39900, "nickname": "Scheduling 26-75 users"},
    {"lookup_key": "SCHEDULING_S3_MONTHLY", "product_key": "SCHEDULING_ONLY", "unit_amount": 69900, "nickname": "Scheduling 76-150 users"},
    {"lookup_key": "BILLING_AUTO_B1_MONTHLY", "product_key": "BILLING_AUTOMATION_BASE", "unit_amount": 39900, "nickname": "Billing Auto 0-150 claims base"},
    {"lookup_key": "BILLING_AUTO_B2_MONTHLY", "product_key": "BILLING_AUTOMATION_BASE", "unit_amount": 59900, "nickname": "Billing Auto 151-400 claims base"},
    {"lookup_key": "BILLING_AUTO_B3_MONTHLY", "product_key": "BILLING_AUTOMATION_BASE", "unit_amount": 99900, "nickname": "Billing Auto 401-1000 claims base"},
    {"lookup_key": "BILLING_AUTO_B4_MONTHLY", "product_key": "BILLING_AUTOMATION_BASE", "unit_amount": 149900, "nickname": "Billing Auto 1001+ claims base"},
    {"lookup_key": "CCT_MONTHLY", "product_key": "CCT_TRANSPORT_OPS_ADDON", "unit_amount": 39900, "nickname": "CCT/Transport Ops monthly"},
    {"lookup_key": "HEMS_MONTHLY", "product_key": "HEMS_ADDON", "unit_amount": 75000, "nickname": "HEMS Ops monthly"},
    {"lookup_key": "TRIP_MONTHLY", "product_key": "TRIP_PACK_ADDON", "unit_amount": 19900, "nickname": "Wisconsin TRIP Pack monthly"},
]


def lambda_handler(event: dict, context: Any) -> dict:
    request_type = event.get("RequestType", "Create")
    if request_type == "Delete":
        _send_cfn_response(event, context, "SUCCESS", {})
        return {}

    if not STRIPE_SECRET_KEY:
        logger.error("STRIPE_SECRET_KEY not set")
        _send_cfn_response(event, context, "FAILED", {}, "STRIPE_SECRET_KEY not configured")
        return {}

    stripe.api_key = STRIPE_SECRET_KEY
    ssm = boto3.client("ssm")

    try:
        product_ids: dict[str, str] = {}
        for p in PRODUCTS:
            existing = _find_product_by_name(p["name"])
            if existing:
                product_ids[p["key"]] = existing.id
                logger.info("product_exists key=%s id=%s", p["key"], existing.id)
            else:
                created = stripe.Product.create(name=p["name"], metadata={"lookup_key": p["key"], "stage": STAGE})
                product_ids[p["key"]] = created.id
                logger.info("product_created key=%s id=%s", p["key"], created.id)
            _ssm_put(ssm, f"{SSM_PREFIX}/products/{p['key']}", product_ids[p["key"]])

        price_ids: dict[str, str] = {}
        for pr in PRICES:
            product_id = product_ids.get(pr["product_key"])
            if not product_id:
                continue
            existing_price = _find_price_by_lookup_key(pr["lookup_key"])
            if existing_price:
                price_ids[pr["lookup_key"]] = existing_price.id
                logger.info("price_exists lookup_key=%s id=%s", pr["lookup_key"], existing_price.id)
            else:
                created_price = stripe.Price.create(
                    product=product_id,
                    unit_amount=pr["unit_amount"],
                    currency="usd",
                    recurring={"interval": "month"},
                    lookup_key=pr["lookup_key"],
                    nickname=pr["nickname"],
                    metadata={"stage": STAGE},
                )
                price_ids[pr["lookup_key"]] = created_price.id
                logger.info("price_created lookup_key=%s id=%s", pr["lookup_key"], created_price.id)
            _ssm_put(ssm, f"{SSM_PREFIX}/prices/{pr['lookup_key']}", price_ids[pr["lookup_key"]])

        _send_cfn_response(event, context, "SUCCESS", {"ProductCount": len(product_ids), "PriceCount": len(price_ids)})
    except Exception as exc:
        logger.exception("stripe_bootstrap_error error=%s", exc)
        _send_cfn_response(event, context, "FAILED", {}, str(exc))
    return {}


def _find_product_by_name(name: str):
    try:
        products = stripe.Product.list(limit=100)
        for p in products.auto_paging_iter():
            if p.name == name:
                return p
    except Exception:
        pass
    return None


def _find_price_by_lookup_key(lookup_key: str):
    try:
        prices = stripe.Price.list(lookup_keys=[lookup_key], limit=1)
        if prices.data:
            return prices.data[0]
    except Exception:
        pass
    return None


def _ssm_put(ssm, name: str, value: str) -> None:
    try:
        ssm.put_parameter(Name=name, Value=value, Type="String", Overwrite=True)
    except Exception as exc:
        logger.warning("ssm_put_failed name=%s error=%s", name, exc)


def _send_cfn_response(event: dict, context: Any, status: str, data: dict, reason: str = "") -> None:
    import urllib.request
    response_url = event.get("ResponseURL")
    if not response_url:
        return
    body = json.dumps({
        "Status": status,
        "Reason": reason or f"See CloudWatch logs: {getattr(context, 'log_stream_name', '')}",
        "PhysicalResourceId": event.get("PhysicalResourceId") or event.get("LogicalResourceId", "stripe-bootstrap"),
        "StackId": event.get("StackId", ""),
        "RequestId": event.get("RequestId", ""),
        "LogicalResourceId": event.get("LogicalResourceId", ""),
        "Data": data,
    }).encode("utf-8")
    req = urllib.request.Request(response_url, data=body, method="PUT", headers={"Content-Type": "", "Content-Length": str(len(body))})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        logger.error("cfn_response_send_failed error=%s", exc)
