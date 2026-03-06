from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Optional

import stripe

logger = logging.getLogger(__name__)


class WebhookReplayError(Exception):
    pass


class StripeWebhookHandler:
    def __init__(self, db_service=None):
        self._db = db_service
        self._processed_events: dict[str, float] = {}

    def verify_and_process(
        self,
        payload: bytes,
        sig_header: str,
        endpoint_secret: Optional[str] = None,
    ) -> dict:
        secret = endpoint_secret or os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        if not secret:
            raise ValueError("Stripe webhook secret not configured")

        event = stripe.Webhook.construct_event(payload, sig_header, secret)
        event_id = event["id"]
        event_type = event["type"]

        if self._is_duplicate(event_id):
            logger.info("stripe_webhook_duplicate event_id=%s type=%s", event_id, event_type)
            return {"status": "duplicate", "event_id": event_id}

        handler = self._get_handler(event_type)
        if handler is None:
            logger.info("stripe_webhook_unhandled type=%s", event_type)
            return {"status": "unhandled", "event_type": event_type}

        try:
            result = handler(event)
            self._mark_processed(event_id)
            logger.info("stripe_webhook_processed event_id=%s type=%s", event_id, event_type)
            return {"status": "processed", "event_id": event_id, "result": result}
        except Exception:
            logger.exception("stripe_webhook_error event_id=%s type=%s", event_id, event_type)
            raise

    def _is_duplicate(self, event_id: str) -> bool:
        if event_id in self._processed_events:
            return True
        if self._db:
            return self._db.webhook_event_exists("stripe", event_id)
        return False

    def _mark_processed(self, event_id: str) -> None:
        self._processed_events[event_id] = time.time()
        if self._db:
            self._db.record_webhook_event("stripe", event_id)

    def _get_handler(self, event_type: str):
        handlers = {
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "checkout.session.completed": self._handle_checkout_completed,
            "payment_intent.succeeded": self._handle_payment_succeeded,
            "charge.dispute.created": self._handle_dispute_created,
        }
        return handlers.get(event_type)

    def _handle_invoice_paid(self, event: dict) -> dict:
        invoice = event["data"]["object"]
        return {
            "invoice_id": invoice["id"],
            "customer": invoice.get("customer"),
            "amount_paid": invoice.get("amount_paid"),
            "status": invoice.get("status"),
        }

    def _handle_invoice_payment_failed(self, event: dict) -> dict:
        invoice = event["data"]["object"]
        # Trigger automated dunning or notification service
        logger.warning(f"Invoice {invoice['id']} payment failed. Customer: {invoice.get('customer')}")
        return {
            "invoice_id": invoice["id"],
            "customer": invoice.get("customer"),
            "attempt_count": invoice.get("attempt_count"),
            "status": "payment_failed_handled"
        }

    def _handle_subscription_created(self, event: dict) -> dict:
        sub = event["data"]["object"]
        sub_id = sub["id"]
        customer_id = sub.get("customer")
        logger.info(f"Subscription {sub_id} created for customer {customer_id}. Triggering provisioning.")
        
        # PROVISIONING LOGIC (Phase 1 Stub)
        # 1. Check if tenant already provisioned.
        # 2. If not, trigger:
        #    - 1-800 Number purchase (Telnyx)
        #    - Agency Record creation (if new)
        #    - Send Welcome Email
        
        try:
             # Placeholder for:
             # self.provisioning_service.provision_new_subscription(sub_id)
             pass
        except Exception as e:
            logger.error(f"Provisioning failed for subscription {sub_id}: {e}")
            raise

        return {"subscription_id": sub_id, "status": sub.get("status"), "provisioning": "triggered"}

    def _handle_subscription_updated(self, event: dict) -> dict:
        sub = event["data"]["object"]
        return {"subscription_id": sub["id"], "status": sub.get("status")}

    def _handle_subscription_deleted(self, event: dict) -> dict:
        sub = event["data"]["object"]
        return {"subscription_id": sub["id"], "canceled_at": sub.get("canceled_at")}

    def _handle_checkout_completed(self, event: dict) -> dict:
        session = event["data"]["object"]
        return {
            "session_id": session["id"],
            "customer": session.get("customer"),
            "payment_status": session.get("payment_status"),
        }

    def _handle_payment_succeeded(self, event: dict) -> dict:
        pi = event["data"]["object"]
        return {"payment_intent_id": pi["id"], "amount": pi.get("amount")}

    def _handle_dispute_created(self, event: dict) -> dict:
        dispute = event["data"]["object"]
        logger.warning("stripe_dispute_created id=%s amount=%s", dispute["id"], dispute.get("amount"))
        return {"dispute_id": dispute["id"], "amount": dispute.get("amount")}


def create_idempotent_key(operation: str, *args: str) -> str:
    raw = f"{operation}:{'|'.join(args)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
