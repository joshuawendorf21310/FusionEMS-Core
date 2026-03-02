"""
Stripe Bootstrap Lambda (CloudFormation custom resource)

Enterprise Production Version

✔ Idempotent product provisioning (metadata search)
✔ Idempotent price provisioning (lookup_key)
✔ Metered pricing support
✔ Stripe Tax support
✔ Billing Portal provisioning
✔ Webhook provisioning (no duplicates)
✔ Secrets Manager or env secret
✔ SSM storage of all IDs
✔ Stable PhysicalResourceId
✔ Safe for Create + Update
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import boto3
import stripe

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ==========================================================
# ENVIRONMENT CONFIG
# ==========================================================

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_SECRET_ARN = os.environ.get("STRIPE_SECRET_ARN")

SSM_PREFIX = os.environ.get("SSM_PREFIX", "/fusionems/dev/stripe")
STAGE = os.environ.get("STAGE", "dev")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

ENABLE_STRIPE_TAX = os.environ.get("ENABLE_STRIPE_TAX", "true").lower() == "true"

# ==========================================================
# PRODUCT + PRICE CONFIG
# (Use versioned keys for safe price evolution)
# ==========================================================

PRODUCTS = [
    {"key": "SCHEDULING_ONLY_V1", "name": "QuantumEMS Scheduling Only"},
    {"key": "FULL_STACK_V1", "name": "QuantumEMS Full Stack"},
    {"key": "BILLING_AUTOMATION_BASE_V1", "name": "Billing Automation Base"},
]

PRICES = [
    {
        "lookup_key": "FULL_STACK_V1_MONTHLY",
        "product_key": "FULL_STACK_V1",
        "unit_amount": 99900,
        "interval": "month",
        "metered": False,
    },
    {
        "lookup_key": "CLAIMS_METERED_V1",
        "product_key": "BILLING_AUTOMATION_BASE_V1",
        "unit_amount": 15,
        "interval": "month",
        "metered": True,
    },
]

# ==========================================================
# ENTRYPOINT
# ==========================================================


def lambda_handler(event: dict, context: Any) -> dict:
    logger.info("stripe_bootstrap_event=%s", json.dumps(event))

    request_type = event.get("RequestType", "Create")
    physical_id = "fusionems-stripe-bootstrap"

    if request_type == "Delete":
        _send_cfn_response(event, context, "SUCCESS", {}, physical_id)
        return {}

    try:
        _configure_stripe()

        ssm = boto3.client("ssm")

        product_ids = _ensure_products(ssm)
        price_ids = _ensure_prices(ssm, product_ids)
        portal_id = _ensure_billing_portal(ssm)
        webhook_secret = _ensure_webhook(ssm)

        data = {
            "ProductCount": len(product_ids),
            "PriceCount": len(price_ids),
            "BillingPortalConfigId": portal_id,
            "WebhookConfigured": bool(webhook_secret),
        }

        _send_cfn_response(event, context, "SUCCESS", data, physical_id)

    except Exception as exc:
        logger.exception("stripe_bootstrap_failed")
        _send_cfn_response(event, context, "FAILED", {}, physical_id, str(exc))

    return {}


# ==========================================================
# STRIPE CONFIGURATION
# ==========================================================


def _configure_stripe():
    if STRIPE_SECRET_ARN:
        secrets = boto3.client("secretsmanager")
        secret = json.loads(
            secrets.get_secret_value(SecretId=STRIPE_SECRET_ARN)["SecretString"]
        )
        stripe.api_key = secret["secret_key"]
    elif STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
    else:
        raise RuntimeError("Stripe secret not configured")


# ==========================================================
# PRODUCTS
# ==========================================================


def _ensure_products(ssm) -> Dict[str, str]:
    product_ids = {}

    for p in PRODUCTS:
        result = stripe.Product.search(
            query=f"metadata['product_key']:'{p['key']}' AND metadata['stage']:'{STAGE}'"
        )

        if result.data:
            product = result.data[0]
            logger.info("product_exists key=%s id=%s", p["key"], product.id)
        else:
            product = stripe.Product.create(
                name=p["name"],
                metadata={"product_key": p["key"], "stage": STAGE},
            )
            logger.info("product_created key=%s id=%s", p["key"], product.id)

        product_ids[p["key"]] = product.id
        _ssm_put(ssm, f"{SSM_PREFIX}/products/{p['key']}", product.id)

    return product_ids


# ==========================================================
# PRICES
# ==========================================================


def _ensure_prices(ssm, product_ids) -> Dict[str, str]:
    price_ids = {}

    for pr in PRICES:
        existing = stripe.Price.list(lookup_keys=[pr["lookup_key"]], limit=1)

        if existing.data:
            price = existing.data[0]
            logger.info("price_exists lookup_key=%s id=%s", pr["lookup_key"], price.id)
        else:
            recurring_config = {"interval": pr["interval"]}

            if pr["metered"]:
                recurring_config["usage_type"] = "metered"

            create_params = {
                "product": product_ids[pr["product_key"]],
                "unit_amount": pr["unit_amount"],
                "currency": "usd",
                "recurring": recurring_config,
                "lookup_key": pr["lookup_key"],
                "metadata": {"stage": STAGE},
            }

            if ENABLE_STRIPE_TAX:
                create_params["automatic_tax"] = {"enabled": True}

            price = stripe.Price.create(**create_params)

            logger.info("price_created lookup_key=%s id=%s", pr["lookup_key"], price.id)

        price_ids[pr["lookup_key"]] = price.id
        _ssm_put(ssm, f"{SSM_PREFIX}/prices/{pr['lookup_key']}", price.id)

    return price_ids


# ==========================================================
# BILLING PORTAL
# ==========================================================


def _ensure_billing_portal(ssm) -> str:
    configs = stripe.billing_portal.Configuration.list(limit=1)

    if configs.data:
        config = configs.data[0]
    else:
        config = stripe.billing_portal.Configuration.create(
            features={
                "subscription_cancel": {"enabled": True},
                "payment_method_update": {"enabled": True},
            }
        )

    _ssm_put(ssm, f"{SSM_PREFIX}/billing_portal/config_id", config.id)
    return config.id


# ==========================================================
# WEBHOOK
# ==========================================================


def _ensure_webhook(ssm) -> str | None:
    if not WEBHOOK_URL:
        return None

    endpoints = stripe.WebhookEndpoint.list(limit=100)

    for ep in endpoints.auto_paging_iter():
        if ep.url == WEBHOOK_URL:
            logger.info("webhook_exists url=%s", WEBHOOK_URL)
            _ssm_put(ssm, f"{SSM_PREFIX}/webhook/secret", ep.secret)
            return ep.secret

    new_ep = stripe.WebhookEndpoint.create(
        url=WEBHOOK_URL,
        enabled_events=[
            "invoice.paid",
            "invoice.payment_failed",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ],
    )

    logger.info("webhook_created url=%s", WEBHOOK_URL)

    _ssm_put(ssm, f"{SSM_PREFIX}/webhook/secret", new_ep.secret)
    return new_ep.secret


# ==========================================================
# SSM
# ==========================================================


def _ssm_put(ssm, name: str, value: str) -> None:
    ssm.put_parameter(Name=name, Value=value, Type="String", Overwrite=True)


# ==========================================================
# CLOUDFORMATION RESPONSE
# ==========================================================


def _send_cfn_response(event, context, status, data, physical_id, reason=""):
    import urllib.request

    body = json.dumps(
        {
            "Status": status,
            "Reason": reason or f"See logs: {context.log_stream_name}",
            "PhysicalResourceId": physical_id,
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
            "Data": data,
        }
    ).encode()

    req = urllib.request.Request(
        event["ResponseURL"],
        data=body,
        method="PUT",
        headers={"Content-Type": "", "Content-Length": str(len(body))},
    )

    urllib.request.urlopen(req, timeout=10)
