from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import stripe

logger = logging.getLogger(__name__)


class StripeNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class StripeConfig:
    secret_key: str
    webhook_secret: str | None = None


def _configure(cfg: StripeConfig) -> None:
    if not cfg.secret_key:
        raise StripeNotConfigured("stripe_secret_key_missing")
    stripe.api_key = cfg.secret_key


def create_connect_checkout_session(
    *,
    cfg: StripeConfig,
    connected_account_id: str,
    amount_cents: int,
    currency: str = "usd",
    statement_id: str,
    tenant_id: str,
    patient_account_ref: str | None,
    lob_letter_id: str | None,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """
    Create a Stripe Checkout Session on the agency's connected account.
    FusionEMS never touches the funds; payment goes directly to the agency.
    """
    _configure(cfg)

    metadata: dict[str, str] = {
        "statement_id": statement_id,
        "tenant_id": tenant_id,
    }
    if patient_account_ref:
        metadata["patient_account_ref"] = patient_account_ref
    if lob_letter_id:
        metadata["lob_letter_id"] = lob_letter_id

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": "Medical Transport — Balance Due",
                        "description": f"Statement {statement_id}",
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        payment_intent_data={"metadata": metadata},
        stripe_account=connected_account_id,
    )

    logger.info(
        "stripe_checkout_created statement_id=%s session_id=%s account=%s",
        statement_id,
        session.id,
        connected_account_id,
    )
    return {
        "checkout_session_id": session.id,
        "checkout_url": session.url,
        "payment_status": session.payment_status,
        "connected_account_id": connected_account_id,
    }


def verify_webhook_signature(
    *,
    cfg: StripeConfig,
    payload: bytes,
    sig_header: str,
) -> dict[str, Any]:
    """
    Verify Stripe-Signature using the raw request body bytes.
    Raises stripe.error.SignatureVerificationError on failure.
    """
    if not cfg.webhook_secret:
        raise StripeNotConfigured("stripe_webhook_secret_missing")
    event = stripe.Webhook.construct_event(payload, sig_header, cfg.webhook_secret)
    return dict(event)


def retrieve_checkout_session(
    *,
    cfg: StripeConfig,
    session_id: str,
    connected_account_id: str,
) -> dict[str, Any]:
    _configure(cfg)
    session = stripe.checkout.Session.retrieve(
        session_id,
        stripe_account=connected_account_id,
    )
    return dict(session)


def create_patient_checkout_session(
    *,
    cfg: StripeConfig,
    amount_cents: int,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, str] | None = None,
    currency: str = "usd",
) -> dict[str, Any]:
    """Create a direct Stripe Checkout Session for patient bill payment."""
    _configure(cfg)
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "unit_amount": amount_cents,
                    "product_data": {"name": "EMS Billing Payment"},
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata or {},
    )
    return dict(session)
