from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Optional

import stripe


class StripeNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class StripeConfig:
    secret_key: str
    webhook_secret: str | None = None


def configure_stripe(cfg: StripeConfig) -> None:
    if not cfg.secret_key:
        raise StripeNotConfigured("stripe_secret_key_missing")
    stripe.api_key = cfg.secret_key


def create_patient_checkout_session(*, cfg: StripeConfig, amount_cents: int, success_url: str, cancel_url: str, metadata: dict[str, str]) -> dict[str, Any]:
    configure_stripe(cfg)
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "EMS Patient Payment"},
                "unit_amount": amount_cents,
            },
            "quantity": 1
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    return {"id": session.id, "url": session.url, "payment_status": session.payment_status}


def verify_webhook_signature(*, cfg: StripeConfig, payload: bytes, sig_header: str) -> dict[str, Any]:
    if not cfg.webhook_secret:
        raise StripeNotConfigured("stripe_webhook_secret_missing")
    event = stripe.Webhook.construct_event(payload, sig_header, cfg.webhook_secret)
    return event
