"""
Tests: Lob/Stripe billing integration
- Lob signature verification (HMAC-SHA256 with timestamp)
- Stripe signature verification (raw body)
- Idempotency (duplicate event handling)
- Payment success flow
- Refund flow
- Lob letter.rendered_pdf -> artifact attached
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_lob_signature(raw_body: bytes, secret: str, ts: int) -> str:
    signed = f"{ts}.{base64.b64encode(raw_body).decode()}"
    return hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()


def _make_stripe_signature(raw_body: bytes, secret: str, ts: int) -> str:
    """
    Construct a Stripe webhook signature header.
    stripe-python uses the full webhook secret string (including whsec_ prefix)
    as the raw UTF-8 HMAC key.
    """
    signed_payload = f"{ts}.{raw_body.decode()}"
    sig = hmac.new(
        secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"t={ts},v1={sig}"


def _fake_lob_letter_id() -> str:
    """Lob letter IDs: ltr_ followed by exactly 22 alphanumeric characters."""
    return "ltr_" + uuid.uuid4().hex[:22]


def _fake_stripe_account_id() -> str:
    """Stripe connected account IDs: acct_ followed by 16 alphanumeric chars."""
    return "acct_" + uuid.uuid4().hex[:16]


# ─────────────────────────────────────────────────────────────────────────────
# Lob signature verification tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLobSignatureVerification:
    SECRET = "lob_test_secret_xyz"

    def test_valid_signature_passes(self):
        from core_app.integrations.lob_service import verify_lob_webhook_signature

        body = b'{"id":"evt_123","event_type":{"id":"letter.created"}}'
        ts = int(time.time())
        sig = _make_lob_signature(body, self.SECRET, ts)

        assert (
            verify_lob_webhook_signature(
                raw_body=body,
                signature_header=sig,
                timestamp_header=str(ts),
                webhook_secret=self.SECRET,
            )
            is True
        )

    def test_wrong_secret_fails(self):
        from core_app.integrations.lob_service import verify_lob_webhook_signature

        body = b'{"id":"evt_123"}'
        ts = int(time.time())
        sig = _make_lob_signature(body, "wrong_secret", ts)

        assert (
            verify_lob_webhook_signature(
                raw_body=body,
                signature_header=sig,
                timestamp_header=str(ts),
                webhook_secret=self.SECRET,
            )
            is False
        )

    def test_tampered_body_fails(self):
        from core_app.integrations.lob_service import verify_lob_webhook_signature

        body = b'{"id":"evt_123"}'
        ts = int(time.time())
        sig = _make_lob_signature(body, self.SECRET, ts)

        tampered = b'{"id":"evt_TAMPERED"}'
        assert (
            verify_lob_webhook_signature(
                raw_body=tampered,
                signature_header=sig,
                timestamp_header=str(ts),
                webhook_secret=self.SECRET,
            )
            is False
        )

    def test_expired_timestamp_fails(self):
        from core_app.integrations.lob_service import verify_lob_webhook_signature

        body = b'{"id":"evt_stale"}'
        ts = int(time.time()) - 400  # 400s ago > 300s tolerance
        sig = _make_lob_signature(body, self.SECRET, ts)

        assert (
            verify_lob_webhook_signature(
                raw_body=body,
                signature_header=sig,
                timestamp_header=str(ts),
                webhook_secret=self.SECRET,
            )
            is False
        )

    def test_missing_secret_fails(self):
        from core_app.integrations.lob_service import verify_lob_webhook_signature

        body = b'{"id":"evt_123"}'
        ts = int(time.time())
        sig = _make_lob_signature(body, self.SECRET, ts)

        assert (
            verify_lob_webhook_signature(
                raw_body=body,
                signature_header=sig,
                timestamp_header=str(ts),
                webhook_secret="",
            )
            is False
        )

    def test_empty_signature_fails(self):
        from core_app.integrations.lob_service import verify_lob_webhook_signature

        body = b'{"id":"evt_123"}'
        ts = int(time.time())

        assert (
            verify_lob_webhook_signature(
                raw_body=body,
                signature_header="",
                timestamp_header=str(ts),
                webhook_secret=self.SECRET,
            )
            is False
        )


# ─────────────────────────────────────────────────────────────────────────────
# Stripe signature verification tests
# ─────────────────────────────────────────────────────────────────────────────


class TestStripeSignatureVerification:
    # stripe-python uses the full whsec_... string as UTF-8 HMAC key
    SECRET = "whsec_" + uuid.uuid4().hex + uuid.uuid4().hex  # whsec_ + 64 hex chars

    def _make_event(self, event_type: str = "payment_intent.succeeded") -> bytes:
        return json.dumps(
            {
                "id": f"evt_{uuid.uuid4().hex[:16]}",
                "type": event_type,
                "data": {
                    "object": {
                        "id": f"pi_{uuid.uuid4().hex[:24]}",
                        "metadata": {"statement_id": str(uuid.uuid4())},
                    }
                },
            }
        ).encode()

    def test_valid_signature_passes(self):
        """Verify real HMAC construction — does NOT patch construct_event."""
        from core_app.payments.stripe_service import StripeConfig, verify_webhook_signature

        body = self._make_event()
        ts = int(time.time())
        sig_header = _make_stripe_signature(body, self.SECRET, ts)

        cfg = StripeConfig(secret_key="sk_test_" + "x" * 24, webhook_secret=self.SECRET)
        event = verify_webhook_signature(cfg=cfg, payload=body, sig_header=sig_header)
        assert event["type"] == "payment_intent.succeeded"

    def test_invalid_signature_raises(self):
        import stripe

        from core_app.payments.stripe_service import StripeConfig, verify_webhook_signature

        body = self._make_event()
        ts = int(time.time())
        bad_sig_header = _make_stripe_signature(body, "whsec_wrong_key_material", ts)

        cfg = StripeConfig(secret_key="sk_test_" + "x" * 24, webhook_secret=self.SECRET)
        with pytest.raises(stripe.error.SignatureVerificationError):
            verify_webhook_signature(cfg=cfg, payload=body, sig_header=bad_sig_header)

    def test_missing_webhook_secret_raises(self):
        from core_app.payments.stripe_service import (
            StripeConfig,
            StripeNotConfigured,
            verify_webhook_signature,
        )

        cfg = StripeConfig(secret_key="sk_test_" + "x" * 24, webhook_secret=None)
        with pytest.raises(StripeNotConfigured):
            verify_webhook_signature(cfg=cfg, payload=b"{}", sig_header="t=1,v1=abc")


# ─────────────────────────────────────────────────────────────────────────────
# Idempotency tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLobWorkerIdempotency:
    def test_duplicate_event_skipped(self):
        from core_app.workers.lob_worker import process_lob_event

        event_id = f"evt_{uuid.uuid4().hex}"
        message = {
            "event_id": event_id,
            "event_type": "letter.created",
            "payload": {"body": {"id": _fake_lob_letter_id(), "metadata": {}}},
            "correlation_id": "test",
        }

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"event_id": event_id, "processed": True}}

        with patch("core_app.workers.lob_worker._table", return_value=mock_table):
            process_lob_event(message)
            mock_table.update_item.assert_not_called()


class TestStripeWorkerIdempotency:
    def test_duplicate_event_skipped(self):
        from core_app.workers.stripe_worker import process_stripe_event

        event_id = f"evt_{uuid.uuid4().hex}"
        message = {
            "event_id": event_id,
            "event_type": "payment_intent.succeeded",
            "connected_account_id": _fake_stripe_account_id(),
            "payload": {"data": {"object": {"metadata": {"statement_id": str(uuid.uuid4())}}}},
            "correlation_id": "test",
        }

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"event_id": event_id, "processed": True}}

        with patch("core_app.workers.stripe_worker._table", return_value=mock_table):
            process_stripe_event(message)
            mock_table.update_item.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Payment success flow
# Workers use module-level table name constants (empty strings in test env).
# Patch both the table-name constants and the _table function so the selector
# can route by name correctly.
# ─────────────────────────────────────────────────────────────────────────────


class TestPaymentSuccessFlow:
    def _run_stripe_event(self, message: dict) -> tuple[MagicMock, MagicMock]:
        mock_events_table = MagicMock()
        mock_events_table.get_item.return_value = {}

        mock_statements_table = MagicMock()
        mock_statements_table.get_item.return_value = {
            "Item": {
                "statement_id": message["payload"]
                .get("data", {})
                .get("object", {})
                .get("metadata", {})
                .get("statement_id", ""),
                "payment_status": "pending",
            }
        }

        def _table_selector(name: str):
            if name == "test-stripe-events":
                return mock_events_table
            if name == "test-statements":
                return mock_statements_table
            return MagicMock()

        with (
            patch("core_app.workers.stripe_worker._table", side_effect=_table_selector),
            patch("core_app.workers.stripe_worker.STRIPE_EVENTS_TABLE", "test-stripe-events"),
            patch("core_app.workers.stripe_worker.STATEMENTS_TABLE", "test-statements"),
            patch("core_app.workers.stripe_worker._resolve_tenant", return_value="tenant_test"),
        ):
            from core_app.workers.stripe_worker import process_stripe_event

            process_stripe_event(message)

        return mock_events_table, mock_statements_table

    def test_checkout_session_completed_marks_paid(self):
        statement_id = str(uuid.uuid4())
        event_id = f"evt_{uuid.uuid4().hex}"

        message = {
            "event_id": event_id,
            "event_type": "checkout.session.completed",
            "connected_account_id": _fake_stripe_account_id(),
            "payload": {
                "id": event_id,
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": f"cs_{uuid.uuid4().hex[:24]}",
                        "metadata": {
                            "statement_id": statement_id,
                            "tenant_id": str(uuid.uuid4()),
                        },
                    }
                },
            },
            "correlation_id": "test-pay-flow",
        }

        mock_events_table = MagicMock()
        mock_events_table.get_item.return_value = {}

        mock_statements_table = MagicMock()
        mock_statements_table.get_item.return_value = {
            "Item": {"statement_id": statement_id, "payment_status": "pending"}
        }

        def _table_selector(name: str):
            if name == "test-stripe-events":
                return mock_events_table
            if name == "test-statements":
                return mock_statements_table
            return MagicMock()

        with (
            patch("core_app.workers.stripe_worker._table", side_effect=_table_selector),
            patch("core_app.workers.stripe_worker.STRIPE_EVENTS_TABLE", "test-stripe-events"),
            patch("core_app.workers.stripe_worker.STATEMENTS_TABLE", "test-statements"),
            patch("core_app.workers.stripe_worker._resolve_tenant", return_value="tenant_test"),
        ):
            from core_app.workers.stripe_worker import process_stripe_event

            process_stripe_event(message)

        update_call = mock_statements_table.update_item.call_args
        assert update_call is not None
        expr_vals = update_call.kwargs["ExpressionAttributeValues"]
        assert expr_vals[":s"] == "paid"

    def test_payment_failed_marks_failed(self):
        statement_id = str(uuid.uuid4())
        event_id = f"evt_{uuid.uuid4().hex}"

        message = {
            "event_id": event_id,
            "event_type": "payment_intent.payment_failed",
            "connected_account_id": _fake_stripe_account_id(),
            "payload": {
                "data": {
                    "object": {
                        "metadata": {"statement_id": statement_id},
                    }
                }
            },
            "correlation_id": "test-fail",
        }

        mock_events_table = MagicMock()
        mock_events_table.get_item.return_value = {}

        mock_statements_table = MagicMock()
        mock_statements_table.get_item.return_value = {
            "Item": {"statement_id": statement_id, "payment_status": "pending"}
        }

        def _table_selector(name: str):
            if name == "test-stripe-events":
                return mock_events_table
            if name == "test-statements":
                return mock_statements_table
            return MagicMock()

        with (
            patch("core_app.workers.stripe_worker._table", side_effect=_table_selector),
            patch("core_app.workers.stripe_worker.STRIPE_EVENTS_TABLE", "test-stripe-events"),
            patch("core_app.workers.stripe_worker.STATEMENTS_TABLE", "test-statements"),
            patch("core_app.workers.stripe_worker._resolve_tenant", return_value=None),
        ):
            from core_app.workers.stripe_worker import process_stripe_event

            process_stripe_event(message)

        update_call = mock_statements_table.update_item.call_args
        assert update_call is not None
        expr_vals = update_call.kwargs["ExpressionAttributeValues"]
        assert expr_vals[":s"] == "failed"


# ─────────────────────────────────────────────────────────────────────────────
# Refund flow
# ─────────────────────────────────────────────────────────────────────────────


class TestRefundFlow:
    def test_charge_refunded_marks_refunded(self):
        statement_id = str(uuid.uuid4())
        event_id = f"evt_{uuid.uuid4().hex}"

        message = {
            "event_id": event_id,
            "event_type": "charge.refunded",
            "connected_account_id": _fake_stripe_account_id(),
            "payload": {
                "data": {
                    "object": {
                        "metadata": {"statement_id": statement_id},
                    }
                }
            },
            "correlation_id": "test-refund",
        }

        mock_events_table = MagicMock()
        mock_events_table.get_item.return_value = {}

        mock_statements_table = MagicMock()
        mock_statements_table.get_item.return_value = {
            "Item": {"statement_id": statement_id, "payment_status": "paid"}
        }

        def _table_selector(name: str):
            if name == "test-stripe-events":
                return mock_events_table
            if name == "test-statements":
                return mock_statements_table
            return MagicMock()

        with (
            patch("core_app.workers.stripe_worker._table", side_effect=_table_selector),
            patch("core_app.workers.stripe_worker.STRIPE_EVENTS_TABLE", "test-stripe-events"),
            patch("core_app.workers.stripe_worker.STATEMENTS_TABLE", "test-statements"),
            patch("core_app.workers.stripe_worker._resolve_tenant", return_value=None),
        ):
            from core_app.workers.stripe_worker import process_stripe_event

            process_stripe_event(message)

        update_call = mock_statements_table.update_item.call_args
        assert update_call is not None
        assert update_call.kwargs["ExpressionAttributeValues"][":s"] == "refunded"


# ─────────────────────────────────────────────────────────────────────────────
# Lob rendered_pdf -> artifact attached
# ─────────────────────────────────────────────────────────────────────────────


class TestLobArtifactAttachment:
    def test_rendered_pdf_url_attached(self):
        from core_app.workers.lob_worker import process_lob_event

        statement_id = str(uuid.uuid4())
        lob_letter_id = _fake_lob_letter_id()
        event_id = f"evt_{uuid.uuid4().hex}"
        pdf_url = f"https://lob-assets.com/letters/{lob_letter_id}.pdf?tok=abc"

        message = {
            "event_id": event_id,
            "event_type": "letter.rendered_pdf",
            "payload": {
                "body": {
                    "id": lob_letter_id,
                    "url": pdf_url,
                    "metadata": {"statement_id": statement_id},
                }
            },
            "correlation_id": "test-rendered",
        }

        mock_events_table = MagicMock()
        mock_events_table.get_item.return_value = {}

        mock_statements_table = MagicMock()
        mock_statements_table.get_item.return_value = {
            "Item": {"statement_id": statement_id, "lob_status": "lob_created"}
        }

        def _table_selector(name: str):
            if name == "test-lob-events":
                return mock_events_table
            if name == "test-statements":
                return mock_statements_table
            return MagicMock()

        with (
            patch("core_app.workers.lob_worker._table", side_effect=_table_selector),
            patch("core_app.workers.lob_worker.LOB_EVENTS_TABLE", "test-lob-events"),
            patch("core_app.workers.lob_worker.STATEMENTS_TABLE", "test-statements"),
        ):
            process_lob_event(message)

        calls = mock_statements_table.update_item.call_args_list
        assert len(calls) == 2  # status update + pdf url update
        pdf_update_call = calls[1]
        expr_vals = pdf_update_call.kwargs["ExpressionAttributeValues"]
        assert expr_vals[":u"] == pdf_url

    def test_thumbnails_attached(self):
        from core_app.workers.lob_worker import process_lob_event

        statement_id = str(uuid.uuid4())
        lob_letter_id = _fake_lob_letter_id()
        event_id = f"evt_{uuid.uuid4().hex}"
        thumbnails = [
            {
                "small": "https://lob/thumb_s.png",
                "medium": "https://lob/thumb_m.png",
                "large": "https://lob/thumb_l.png",
            }
        ]

        message = {
            "event_id": event_id,
            "event_type": "letter.rendered_thumbnails",
            "payload": {
                "body": {
                    "id": lob_letter_id,
                    "thumbnails": thumbnails,
                    "metadata": {"statement_id": statement_id},
                }
            },
            "correlation_id": "test-thumbs",
        }

        mock_events_table = MagicMock()
        mock_events_table.get_item.return_value = {}

        mock_statements_table = MagicMock()
        mock_statements_table.get_item.return_value = {
            "Item": {"statement_id": statement_id, "lob_status": "lob_created"}
        }

        def _table_selector(name: str):
            if name == "test-lob-events":
                return mock_events_table
            if name == "test-statements":
                return mock_statements_table
            return MagicMock()

        with (
            patch("core_app.workers.lob_worker._table", side_effect=_table_selector),
            patch("core_app.workers.lob_worker.LOB_EVENTS_TABLE", "test-lob-events"),
            patch("core_app.workers.lob_worker.STATEMENTS_TABLE", "test-statements"),
        ):
            process_lob_event(message)

        calls = mock_statements_table.update_item.call_args_list
        assert len(calls) == 2  # status update + thumbnails update
        thumb_call = calls[1]
        expr_vals = thumb_call.kwargs["ExpressionAttributeValues"]
        assert expr_vals[":t"] == thumbnails


# ─────────────────────────────────────────────────────────────────────────────
# Outbound PDF hash verification
# ─────────────────────────────────────────────────────────────────────────────


class TestOutboundPdfHash:
    def test_hash_mismatch_raises(self):
        from core_app.integrations.lob_service import send_statement_letter

        with pytest.raises(ValueError, match="outbound_sha256 mismatch"):
            send_statement_letter(
                pdf_bytes=b"some pdf bytes",
                outbound_sha256="0" * 64,
                statement_id=str(uuid.uuid4()),
                template_version="v1.0.0",
                to_address={
                    "name": "Jane Doe",
                    "line1": "123 Main St",
                    "city": "Portland",
                    "state": "OR",
                    "zip": "97201",
                },
                from_address={
                    "name": "Agency",
                    "line1": "456 HQ Ave",
                    "city": "Portland",
                    "state": "OR",
                    "zip": "97201",
                },
            )

    def test_correct_hash_accepted(self):
        pdf_bytes = b"fake pdf bytes for hash test"
        correct_hash = hashlib.sha256(pdf_bytes).hexdigest()

        with (
            patch("core_app.integrations.lob_service._get_lob_config") as mock_cfg,
            patch("requests.post") as mock_post,
        ):
            mock_cfg.return_value = MagicMock(api_key="test_live_xxx")
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {
                "id": _fake_lob_letter_id(),
                "expected_delivery_date": "2026-03-05",
            }
            mock_post.return_value = mock_resp

            from core_app.integrations.lob_service import send_statement_letter

            result = send_statement_letter(
                pdf_bytes=pdf_bytes,
                outbound_sha256=correct_hash,
                statement_id=str(uuid.uuid4()),
                template_version="v1.0.0",
                to_address={
                    "name": "Jane Doe",
                    "line1": "123 Main St",
                    "city": "Portland",
                    "state": "OR",
                    "zip": "97201",
                },
                from_address={
                    "name": "Agency",
                    "line1": "456 HQ Ave",
                    "city": "Portland",
                    "state": "OR",
                    "zip": "97201",
                },
            )
            assert result["id"].startswith("ltr_")


# ─────────────────────────────────────────────────────────────────────────────
# Status machine ordering
# ─────────────────────────────────────────────────────────────────────────────


class TestStatusMachineOrdering:
    def test_lob_status_does_not_downgrade(self):
        from core_app.workers.lob_worker import _update_statement_lob_status

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"statement_id": "stmt_1", "lob_status": "lob_billed"}
        }

        with (
            patch("core_app.workers.lob_worker._table", return_value=mock_table),
            patch("core_app.workers.lob_worker.STATEMENTS_TABLE", "test-statements"),
        ):
            _update_statement_lob_status(
                statement_id="stmt_1",
                lob_letter_id=_fake_lob_letter_id(),
                new_status="lob_created",
                event_type="letter.created",
                payload={},
                correlation_id="test",
            )
        mock_table.update_item.assert_not_called()

    def test_stripe_paid_not_downgraded_to_failed(self):
        from core_app.workers.stripe_worker import _update_statement_payment_status

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"statement_id": "stmt_1", "payment_status": "paid"}
        }

        with (
            patch("core_app.workers.stripe_worker._table", return_value=mock_table),
            patch("core_app.workers.stripe_worker.STATEMENTS_TABLE", "test-statements"),
        ):
            _update_statement_payment_status(
                statement_id="stmt_1",
                new_status="failed",
                event_type="payment_intent.payment_failed",
                event_id=f"evt_{uuid.uuid4().hex}",
                payload={},
                tenant_id=None,
                correlation_id="test",
            )
        mock_table.update_item.assert_not_called()
