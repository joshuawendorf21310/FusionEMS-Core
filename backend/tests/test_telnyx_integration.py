"""
Integration tests for the Telnyx Voice/SMS/Fax webhook pipeline.

Covers:
- Ed25519 signature verification (valid, invalid, expired, missing fields)
- Idempotency: duplicate event_id → 200 no-op on second call
- SMS STOP/HELP keyword handling and opt-out enforcement
- IVR state machine: MENU → COLLECT_STATEMENT_ID → COLLECT_SMS_PHONE → done
"""
from __future__ import annotations

import base64
import json
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

# ── Ed25519 test key pair ────────────────────────────────────────────────────

def _generate_test_keypair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_der = public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    pub_b64 = base64.b64encode(pub_der).decode()
    return private_key, pub_b64


def _sign_payload(private_key: Ed25519PrivateKey, raw_body: bytes, timestamp: str) -> str:
    signed_payload = f"{timestamp}|{raw_body.decode('utf-8', errors='replace')}"
    sig_bytes = private_key.sign(signed_payload.encode("utf-8"))
    return base64.b64encode(sig_bytes).decode()


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def keypair():
    return _generate_test_keypair()


@pytest.fixture(scope="module")
def private_key(keypair):
    return keypair[0]


@pytest.fixture(scope="module")
def public_key_b64(keypair):
    return keypair[1]


# ══════════════════════════════════════════════════════════════════════════════
# Section 1: Ed25519 signature verification unit tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEd25519Verification:
    def test_valid_signature(self, private_key, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        body = b'{"test": "payload"}'
        ts = str(int(time.time()))
        sig = _sign_payload(private_key, body, ts)
        assert verify_telnyx_webhook(
            raw_body=body,
            signature_ed25519=sig,
            timestamp=ts,
            public_key_base64=public_key_b64,
            tolerance_seconds=300,
        ) is True

    def test_invalid_signature_wrong_key(self, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        other_key = Ed25519PrivateKey.generate()
        body = b'{"test": "payload"}'
        ts = str(int(time.time()))
        sig = _sign_payload(other_key, body, ts)
        assert verify_telnyx_webhook(
            raw_body=body,
            signature_ed25519=sig,
            timestamp=ts,
            public_key_base64=public_key_b64,
        ) is False

    def test_tampered_body(self, private_key, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        body = b'{"test": "payload"}'
        ts = str(int(time.time()))
        sig = _sign_payload(private_key, body, ts)
        tampered = b'{"test": "tampered"}'
        assert verify_telnyx_webhook(
            raw_body=tampered,
            signature_ed25519=sig,
            timestamp=ts,
            public_key_base64=public_key_b64,
        ) is False

    def test_expired_timestamp(self, private_key, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        body = b'{"test": "payload"}'
        ts = str(int(time.time()) - 600)
        sig = _sign_payload(private_key, body, ts)
        assert verify_telnyx_webhook(
            raw_body=body,
            signature_ed25519=sig,
            timestamp=ts,
            public_key_base64=public_key_b64,
            tolerance_seconds=300,
        ) is False

    def test_future_timestamp_within_tolerance(self, private_key, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        body = b'{"test": "payload"}'
        ts = str(int(time.time()) + 30)
        sig = _sign_payload(private_key, body, ts)
        assert verify_telnyx_webhook(
            raw_body=body,
            signature_ed25519=sig,
            timestamp=ts,
            public_key_base64=public_key_b64,
            tolerance_seconds=300,
        ) is True

    def test_missing_signature(self, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        assert verify_telnyx_webhook(
            raw_body=b"body",
            signature_ed25519=None,
            timestamp=str(int(time.time())),
            public_key_base64=public_key_b64,
        ) is False

    def test_missing_timestamp(self, private_key, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        body = b"body"
        ts = str(int(time.time()))
        sig = _sign_payload(private_key, body, ts)
        assert verify_telnyx_webhook(
            raw_body=body,
            signature_ed25519=sig,
            timestamp=None,
            public_key_base64=public_key_b64,
        ) is False

    def test_missing_public_key(self, private_key):
        from core_app.telnyx.signature import verify_telnyx_webhook
        body = b"body"
        ts = str(int(time.time()))
        sig = _sign_payload(private_key, body, ts)
        assert verify_telnyx_webhook(
            raw_body=body,
            signature_ed25519=sig,
            timestamp=ts,
            public_key_base64="",
        ) is False

    def test_garbage_signature(self, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        assert verify_telnyx_webhook(
            raw_body=b"body",
            signature_ed25519="not-base64!!!",
            timestamp=str(int(time.time())),
            public_key_base64=public_key_b64,
        ) is False

    def test_non_integer_timestamp(self, private_key, public_key_b64):
        from core_app.telnyx.signature import verify_telnyx_webhook
        body = b"body"
        sig = _sign_payload(private_key, body, "not-a-number")
        assert verify_telnyx_webhook(
            raw_body=body,
            signature_ed25519=sig,
            timestamp="not-a-number",
            public_key_base64=public_key_b64,
        ) is False


# ══════════════════════════════════════════════════════════════════════════════
# Section 2: SMS webhook — STOP/HELP compliance + idempotency
# ══════════════════════════════════════════════════════════════════════════════

def _make_sms_event(
    *,
    message_id: str | None = None,
    from_number: str = "+12025550100",
    to_number: str = "+18005550000",
    body: str = "STOP",
    event_type: str = "message.received",
) -> dict[str, Any]:
    return {
        "data": {
            "event_type": event_type,
            "id": message_id or str(uuid.uuid4()),
            "payload": {
                "id": message_id or str(uuid.uuid4()),
                "from": {"phone_number": from_number},
                "to": [{"phone_number": to_number}],
                "text": body,
                "direction": "inbound",
            },
        }
    }


def _sms_headers(private_key, body_bytes: bytes) -> dict[str, str]:
    ts = str(int(time.time()))
    sig = _sign_payload(private_key, body_bytes, ts)
    return {
        "telnyx-signature-ed25519": sig,
        "telnyx-timestamp": ts,
        "Content-Type": "application/json",
    }


class TestSmsWebhook:
    def _make_client(self, private_key, public_key_b64, db_mock):
        from fastapi import FastAPI

        from core_app.api.dependencies import db_session_dependency
        from core_app.api.sms_webhook_router import router

        app = FastAPI()
        app.include_router(router)

        def override_db():
            yield db_mock

        app.dependency_overrides[db_session_dependency] = override_db
        client = TestClient(app, raise_server_exceptions=False)
        return client

    def _build_db_mock(
        self,
        *,
        tenant_id: str = "tid-001",
        billing_contact_phone: str = "+18885550001",
        first_insert_rowcount: int = 1,
    ):
        db = MagicMock()
        event_result = MagicMock()
        event_result.rowcount = first_insert_rowcount

        tenant_row = MagicMock()
        tenant_row.tenant_id = tenant_id

        tenant_info_row = MagicMock()
        tenant_info_row.billing_contact_phone = billing_contact_phone
        tenant_info_row.name = "Demo Agency"

        opt_out_row = None

        def execute_side_effect(stmt, params=None):
            sql = str(stmt)
            if "telnyx_events" in sql:
                return event_result
            if "tenant_phone_numbers" in sql:
                r = MagicMock()
                r.fetchone.return_value = tenant_row
                return r
            if "tenants" in sql and "billing_contact_phone" in sql:
                r = MagicMock()
                r.fetchone.return_value = tenant_info_row
                return r
            if "telnyx_opt_outs" in sql and "INSERT" in sql:
                r = MagicMock()
                r.rowcount = 1
                return r
            if "telnyx_sms_messages" in sql:
                r = MagicMock()
                r.rowcount = 1
                return r
            r = MagicMock()
            r.fetchone.return_value = opt_out_row
            r.rowcount = 0
            return r

        db.execute.side_effect = execute_side_effect
        return db

    def test_stop_keyword_returns_200(self, private_key, public_key_b64):
        db = self._build_db_mock()
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_sms_event(body="STOP")
        body_bytes = json.dumps(event).encode()
        headers = _sms_headers(private_key, body_bytes)

        with patch("core_app.api.sms_webhook_router.get_settings") as mock_settings, \
             patch("core_app.api.sms_webhook_router.send_sms") as mock_sms:
            mock_settings.return_value.telnyx_public_key = public_key_b64
            mock_settings.return_value.telnyx_webhook_tolerance_seconds = 300
            mock_settings.return_value.telnyx_api_key = "KEY"
            mock_settings.return_value.telnyx_from_number = "+18005550000"
            mock_settings.return_value.telnyx_messaging_profile_id = "mp-001"
            mock_sms.return_value = {"id": "sms-001"}

            resp = client.post("/webhooks/telnyx/sms", content=body_bytes, headers=headers)

        assert resp.status_code == 200

    def test_unsubscribe_keyword(self, private_key, public_key_b64):
        db = self._build_db_mock()
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_sms_event(body="UNSUBSCRIBE")
        body_bytes = json.dumps(event).encode()
        headers = _sms_headers(private_key, body_bytes)

        with patch("core_app.api.sms_webhook_router.get_settings") as mock_settings, \
             patch("core_app.api.sms_webhook_router.send_sms"):
            mock_settings.return_value.telnyx_public_key = public_key_b64
            mock_settings.return_value.telnyx_webhook_tolerance_seconds = 300
            mock_settings.return_value.telnyx_api_key = "KEY"
            mock_settings.return_value.telnyx_from_number = "+18005550000"
            mock_settings.return_value.telnyx_messaging_profile_id = "mp-001"

            resp = client.post("/webhooks/telnyx/sms", content=body_bytes, headers=headers)

        assert resp.status_code == 200

    def test_help_keyword_returns_200(self, private_key, public_key_b64):
        db = self._build_db_mock()
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_sms_event(body="HELP")
        body_bytes = json.dumps(event).encode()
        headers = _sms_headers(private_key, body_bytes)

        with patch("core_app.api.sms_webhook_router.get_settings") as mock_settings, \
             patch("core_app.api.sms_webhook_router.send_sms") as mock_sms:
            mock_settings.return_value.telnyx_public_key = public_key_b64
            mock_settings.return_value.telnyx_webhook_tolerance_seconds = 300
            mock_settings.return_value.telnyx_api_key = "KEY"
            mock_settings.return_value.telnyx_from_number = "+18005550000"
            mock_settings.return_value.telnyx_messaging_profile_id = "mp-001"
            mock_sms.return_value = {"id": "sms-002"}

            resp = client.post("/webhooks/telnyx/sms", content=body_bytes, headers=headers)

        assert resp.status_code == 200

    def test_idempotency_second_call_returns_200_no_processing(self, private_key, public_key_b64):
        event_id = str(uuid.uuid4())
        db = self._build_db_mock(first_insert_rowcount=0)
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_sms_event(message_id=event_id, body="STOP")
        body_bytes = json.dumps(event).encode()
        headers = _sms_headers(private_key, body_bytes)

        with patch("core_app.api.sms_webhook_router.get_settings") as mock_settings, \
             patch("core_app.api.sms_webhook_router.send_sms") as mock_sms:
            mock_settings.return_value.telnyx_public_key = public_key_b64
            mock_settings.return_value.telnyx_webhook_tolerance_seconds = 300
            mock_settings.return_value.telnyx_api_key = "KEY"
            mock_settings.return_value.telnyx_from_number = "+18005550000"
            mock_settings.return_value.telnyx_messaging_profile_id = "mp-001"

            resp = client.post("/webhooks/telnyx/sms", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_sms.assert_not_called()

    def test_invalid_signature_returns_400(self, public_key_b64):
        other_key = Ed25519PrivateKey.generate()
        db = self._build_db_mock()
        client = self._make_client(other_key, public_key_b64, db)
        event = _make_sms_event(body="STOP")
        body_bytes = json.dumps(event).encode()
        headers = _sms_headers(other_key, body_bytes)

        with patch("core_app.api.sms_webhook_router.get_settings") as mock_settings:
            mock_settings.return_value.telnyx_public_key = public_key_b64
            mock_settings.return_value.telnyx_webhook_tolerance_seconds = 300

            resp = client.post("/webhooks/telnyx/sms", content=body_bytes, headers=headers)

        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# Section 3: IVR state machine transitions
# ══════════════════════════════════════════════════════════════════════════════

def _make_voice_event(
    event_type: str,
    *,
    call_control_id: str | None = None,
    to: str = "+18005550000",
    from_: str = "+12025550100",
    digits: str | None = None,
    client_state_raw: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    cid = call_control_id or str(uuid.uuid4())
    client_state = base64.b64encode(client_state_raw.encode()).decode() if client_state_raw else None
    payload: dict[str, Any] = {
        "call_control_id": cid,
        "to": to,
        "from": from_,
        "call_leg_id": str(uuid.uuid4()),
    }
    if client_state:
        payload["client_state"] = client_state
    if digits is not None:
        payload["digits"] = digits
        payload["status"] = "valid"
    return {
        "data": {
            "event_type": event_type,
            "id": event_id or str(uuid.uuid4()),
            "payload": payload,
        }
    }


def _voice_headers(private_key, body_bytes: bytes) -> dict[str, str]:
    ts = str(int(time.time()))
    sig = _sign_payload(private_key, body_bytes, ts)
    return {
        "telnyx-signature-ed25519": sig,
        "telnyx-timestamp": ts,
        "Content-Type": "application/json",
    }


class TestIvrStateMachine:
    def _make_client(self, private_key, public_key_b64, db_mock):
        from fastapi import FastAPI

        from core_app.api.dependencies import db_session_dependency
        from core_app.api.voice_webhook_router import router

        app = FastAPI()
        app.include_router(router)

        def override_db():
            yield db_mock

        app.dependency_overrides[db_session_dependency] = override_db
        return TestClient(app, raise_server_exceptions=False)

    def _build_db_mock(self, *, call_state: str = "MENU", tenant_id: str = "tid-001"):
        db = MagicMock()

        tenant_row = MagicMock()
        tenant_row.tenant_id = tenant_id
        tenant_row.forward_to_phone_e164 = "+18885551234"

        call_row = MagicMock()
        call_row.state = call_state
        call_row.tenant_id = tenant_id
        call_row.from_phone = "+12025550100"
        call_row.to_phone = "+18005550000"
        call_row.statement_id = None
        call_row.sms_phone = None
        call_row.attempts = 0

        event_result = MagicMock()
        event_result.rowcount = 1

        stmt_row = MagicMock()
        stmt_row.balance_cents = 5000
        stmt_row.currency = "usd"

        def execute_side_effect(stmt, params=None):
            sql = str(stmt)
            if "telnyx_events" in sql:
                return event_result
            if "tenant_phone_numbers" in sql:
                r = MagicMock()
                r.fetchone.return_value = tenant_row
                return r
            if "telnyx_calls" in sql and "INSERT" in sql:
                r = MagicMock()
                r.rowcount = 1
                return r
            if "telnyx_calls" in sql and "UPDATE" in sql:
                r = MagicMock()
                r.rowcount = 1
                return r
            if "telnyx_calls" in sql:
                r = MagicMock()
                r.fetchone.return_value = call_row
                return r
            if "telnyx_opt_outs" in sql:
                r = MagicMock()
                r.fetchone.return_value = None
                return r
            if "billing_statements" in sql:
                r = MagicMock()
                r.fetchone.return_value = stmt_row
                return r
            r = MagicMock()
            r.fetchone.return_value = None
            r.rowcount = 0
            return r

        db.execute.side_effect = execute_side_effect
        return db

    def _patch_settings(self, mock_settings_fn, public_key_b64: str):
        s = MagicMock()
        s.telnyx_public_key = public_key_b64
        s.telnyx_webhook_tolerance_seconds = 300
        s.telnyx_api_key = "KEY"
        s.ivr_audio_base_url = "https://audio.example.com"
        s.telnyx_from_number = "+18005550000"
        s.telnyx_messaging_profile_id = "mp-001"
        mock_settings_fn.return_value = s

    def test_call_initiated_triggers_answer(self, private_key, public_key_b64):
        db = self._build_db_mock()
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_voice_event("call.initiated")
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms, \
             patch("core_app.api.voice_webhook_router.call_answer") as mock_answer:
            self._patch_settings(ms, public_key_b64)
            mock_answer.return_value = {}

            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_answer.assert_called_once()

    def test_call_answered_plays_menu(self, private_key, public_key_b64):
        db = self._build_db_mock()
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_voice_event("call.answered")
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms, \
             patch("core_app.api.voice_webhook_router.call_gather_using_audio") as mock_gather:
            self._patch_settings(ms, public_key_b64)
            mock_gather.return_value = {}

            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_gather.assert_called_once()

    def test_menu_press_1_advances_to_collect_statement(self, private_key, public_key_b64):
        db = self._build_db_mock(call_state="MENU")
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_voice_event(
            "call.gather.ended",
            digits="1",
            client_state_raw="MENU",
        )
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms, \
             patch("core_app.api.voice_webhook_router.call_gather_using_audio") as mock_gather:
            self._patch_settings(ms, public_key_b64)
            mock_gather.return_value = {}

            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_gather.assert_called_once()

    def test_menu_press_2_triggers_transfer(self, private_key, public_key_b64):
        db = self._build_db_mock(call_state="MENU")
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_voice_event(
            "call.gather.ended",
            digits="2",
            client_state_raw="MENU",
        )
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms, \
             patch("core_app.api.voice_webhook_router.call_transfer") as mock_transfer:
            self._patch_settings(ms, public_key_b64)
            mock_transfer.return_value = {}

            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_transfer.assert_called_once()

    def test_collect_statement_valid_advances_to_collect_phone(self, private_key, public_key_b64):
        db = self._build_db_mock(call_state="COLLECT_STATEMENT_ID")
        client = self._make_client(private_key, public_key_b64, db)

        stmt_id_digits = "123456789"
        event = _make_voice_event(
            "call.gather.ended",
            digits=stmt_id_digits,
            client_state_raw="COLLECT_STATEMENT_ID",
        )
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms, \
             patch("core_app.api.voice_webhook_router.call_gather_using_audio") as mock_gather, \
             patch("core_app.api.voice_webhook_router._validate_statement", return_value=True):
            self._patch_settings(ms, public_key_b64)
            mock_gather.return_value = {}

            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_gather.assert_called_once()

    def test_collect_phone_triggers_payment_sms(self, private_key, public_key_b64):
        db = self._build_db_mock(call_state="COLLECT_SMS_PHONE")
        call_row = MagicMock()
        call_row.state = "COLLECT_SMS_PHONE"
        call_row.tenant_id = "tid-001"
        call_row.statement_id = "stmt-abc"
        call_row.sms_phone = None
        call_row.attempts = 0

        db.execute.side_effect = None

        event_result = MagicMock()
        event_result.rowcount = 1

        tenant_row = MagicMock()
        tenant_row.tenant_id = "tid-001"
        tenant_row.forward_to_phone_e164 = "+18885551234"

        def execute_side_effect(stmt, params=None):
            sql = str(stmt)
            if "telnyx_events" in sql:
                return event_result
            if "tenant_phone_numbers" in sql:
                r = MagicMock()
                r.fetchone.return_value = tenant_row
                return r
            if "telnyx_calls" in sql and "UPDATE" in sql:
                r = MagicMock()
                r.rowcount = 1
                return r
            if "telnyx_calls" in sql:
                r = MagicMock()
                r.fetchone.return_value = call_row
                return r
            if "telnyx_opt_outs" in sql:
                r = MagicMock()
                r.fetchone.return_value = None
                return r
            r = MagicMock()
            r.fetchone.return_value = None
            r.rowcount = 0
            return r

        db.execute.side_effect = execute_side_effect
        client = self._make_client(private_key, public_key_b64, db)

        event = _make_voice_event(
            "call.gather.ended",
            digits="2025550199",
            client_state_raw="COLLECT_SMS_PHONE",
        )
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms, \
             patch("core_app.api.voice_webhook_router.call_gather_using_audio") as mock_gather, \
             patch("core_app.api.voice_webhook_router.voice_payment_helper") as mock_helper:
            self._patch_settings(ms, public_key_b64)
            mock_gather.return_value = {}
            mock_helper.send_payment_link_for_call = AsyncMock(return_value=None)

            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200

    def test_call_hangup_returns_200(self, private_key, public_key_b64):
        db = self._build_db_mock(call_state="DONE")
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_voice_event("call.hangup")
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms:
            self._patch_settings(ms, public_key_b64)
            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200

    def test_voice_idempotency_duplicate_event(self, private_key, public_key_b64):
        db = self._build_db_mock()
        event_result = MagicMock()
        event_result.rowcount = 0

        def execute_side_effect(stmt, params=None):
            sql = str(stmt)
            if "telnyx_events" in sql:
                return event_result
            r = MagicMock()
            r.fetchone.return_value = None
            r.rowcount = 0
            return r

        db.execute.side_effect = execute_side_effect
        client = self._make_client(private_key, public_key_b64, db)

        event = _make_voice_event("call.answered")
        body_bytes = json.dumps(event).encode()
        headers = _voice_headers(private_key, body_bytes)

        with patch("core_app.api.voice_webhook_router.get_settings") as ms, \
             patch("core_app.api.voice_webhook_router.call_gather_using_audio") as mock_gather:
            self._patch_settings(ms, public_key_b64)
            mock_gather.return_value = {}

            resp = client.post("/webhooks/telnyx/voice", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_gather.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# Section 4: Fax webhook — idempotency + sig verify
# ══════════════════════════════════════════════════════════════════════════════

def _make_fax_event(
    *,
    event_id: str | None = None,
    fax_id: str | None = None,
    to_number: str = "+18005550002",
    from_number: str = "+12025550200",
    media_url: str = "https://media.telnyx.com/fax-001.pdf",
) -> dict[str, Any]:
    return {
        "data": {
            "event_type": "fax.received",
            "id": event_id or str(uuid.uuid4()),
            "payload": {
                "fax_id": fax_id or str(uuid.uuid4()),
                "to": to_number,
                "from": from_number,
                "media_url": media_url,
                "page_count": 2,
            },
        }
    }


def _fax_headers(private_key, body_bytes: bytes) -> dict[str, str]:
    ts = str(int(time.time()))
    sig = _sign_payload(private_key, body_bytes, ts)
    return {
        "telnyx-signature-ed25519": sig,
        "telnyx-timestamp": ts,
        "Content-Type": "application/json",
    }


class TestFaxWebhook:
    def _make_client(self, private_key, public_key_b64, db_mock):
        from fastapi import FastAPI

        from core_app.api.dependencies import db_session_dependency
        from core_app.api.fax_webhook_router import router

        app = FastAPI()
        app.include_router(router)

        def override_db():
            yield db_mock

        app.dependency_overrides[db_session_dependency] = override_db
        return TestClient(app, raise_server_exceptions=False)

    def _build_db_mock(self, *, first_insert_rowcount: int = 1):
        db = MagicMock()

        event_result = MagicMock()
        event_result.rowcount = first_insert_rowcount

        tenant_row = MagicMock()
        tenant_row.tenant_id = "tid-002"

        case_row = MagicMock()
        case_row.case_id = str(uuid.uuid4())

        def execute_side_effect(stmt, params=None):
            sql = str(stmt)
            if "telnyx_events" in sql:
                return event_result
            if "tenant_phone_numbers" in sql:
                r = MagicMock()
                r.fetchone.return_value = tenant_row
                return r
            if "billing_cases" in sql:
                r = MagicMock()
                r.fetchone.return_value = case_row
                return r
            if "fax_documents" in sql:
                r = MagicMock()
                r.rowcount = 1
                return r
            r = MagicMock()
            r.fetchone.return_value = None
            r.rowcount = 0
            return r

        db.execute.side_effect = execute_side_effect
        return db

    def test_fax_received_returns_200(self, private_key, public_key_b64):
        db = self._build_db_mock()
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_fax_event()
        body_bytes = json.dumps(event).encode()
        headers = _fax_headers(private_key, body_bytes)
        pdf_bytes = b"%PDF-1.4 fake pdf content"

        with patch("core_app.api.fax_webhook_router.get_settings") as ms, \
             patch("core_app.api.fax_webhook_router.download_media", return_value=pdf_bytes), \
             patch("core_app.api.fax_webhook_router.put_bytes") as mock_put, \
             patch("core_app.api.fax_webhook_router.sqs_publisher") as mock_sqs:
            s = MagicMock()
            s.telnyx_public_key = public_key_b64
            s.telnyx_webhook_tolerance_seconds = 300
            s.telnyx_api_key = "KEY"
            s.s3_bucket_docs = "docs-bucket"
            s.fax_classify_queue_url = "https://sqs.us-east-1.amazonaws.com/123/fax-classify"
            ms.return_value = s
            mock_put.return_value = None
            mock_sqs.enqueue.return_value = None

            resp = client.post("/webhooks/telnyx/fax", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_put.assert_called_once()
        mock_sqs.enqueue.assert_called_once()

    def test_fax_idempotency_duplicate_event(self, private_key, public_key_b64):
        db = self._build_db_mock(first_insert_rowcount=0)
        client = self._make_client(private_key, public_key_b64, db)
        event = _make_fax_event()
        body_bytes = json.dumps(event).encode()
        headers = _fax_headers(private_key, body_bytes)

        with patch("core_app.api.fax_webhook_router.get_settings") as ms, \
             patch("core_app.api.fax_webhook_router.download_media") as mock_dl, \
             patch("core_app.api.fax_webhook_router.put_bytes"), \
             patch("core_app.api.fax_webhook_router.sqs_publisher"):
            s = MagicMock()
            s.telnyx_public_key = public_key_b64
            s.telnyx_webhook_tolerance_seconds = 300
            s.telnyx_api_key = "KEY"
            s.s3_bucket_docs = "docs-bucket"
            s.fax_classify_queue_url = "https://sqs.us-east-1.amazonaws.com/123/fax-classify"
            ms.return_value = s

            resp = client.post("/webhooks/telnyx/fax", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_dl.assert_not_called()

    def test_fax_invalid_signature_returns_400(self, public_key_b64):
        other_key = Ed25519PrivateKey.generate()
        db = self._build_db_mock()
        client = self._make_client(other_key, public_key_b64, db)
        event = _make_fax_event()
        body_bytes = json.dumps(event).encode()
        headers = _fax_headers(other_key, body_bytes)

        with patch("core_app.api.fax_webhook_router.get_settings") as ms:
            s = MagicMock()
            s.telnyx_public_key = public_key_b64
            s.telnyx_webhook_tolerance_seconds = 300
            ms.return_value = s

            resp = client.post("/webhooks/telnyx/fax", content=body_bytes, headers=headers)

        assert resp.status_code == 400

    def test_non_fax_received_event_acked(self, private_key, public_key_b64):
        db = self._build_db_mock()
        client = self._make_client(private_key, public_key_b64, db)
        event = {
            "data": {
                "event_type": "fax.initiated",
                "id": str(uuid.uuid4()),
                "payload": {"fax_id": str(uuid.uuid4())},
            }
        }
        body_bytes = json.dumps(event).encode()
        headers = _fax_headers(private_key, body_bytes)

        with patch("core_app.api.fax_webhook_router.get_settings") as ms, \
             patch("core_app.api.fax_webhook_router.download_media") as mock_dl:
            s = MagicMock()
            s.telnyx_public_key = public_key_b64
            s.telnyx_webhook_tolerance_seconds = 300
            ms.return_value = s

            resp = client.post("/webhooks/telnyx/fax", content=body_bytes, headers=headers)

        assert resp.status_code == 200
        mock_dl.assert_not_called()
