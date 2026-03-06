from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import uuid
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

LOB_API_BASE = "https://api.lob.com/v1"


class LobNotConfigured(Exception):
    pass


@dataclass(frozen=True)
class LobConfig:
    """Legacy config shape used by older routers.

    Newer code paths should prefer `LobService` directly.
    """

    api_key: str


class LobApiError(Exception):
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Lob API error {status_code}: {body}")


def _get_api_key() -> str:
    key = os.environ.get("LOB_API_KEY")
    if not key:
        raise LobNotConfigured("LOB_API_KEY not set")
    return key


def _get_lob_config() -> LobConfig:
    """Backwards-compatible helper for older routers.

    Some endpoints import `_get_lob_config()` at module import time; keeping this
    function prevents import-time crashes in deployments where those routes are
    still registered.
    """

    return LobConfig(api_key=_get_api_key())


def _redact_pii(text: str) -> str:
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]", text)
    text = re.sub(r"\b\d{9}\b", "[SSN_REDACTED]", text)
    return text


class LobService:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    def _key(self) -> str:
        return self._api_key or _get_api_key()

    async def send_letter(
        self,
        to_address: dict,
        from_address: dict,
        template_id: str,
        merge_variables: dict,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        safe_vars = {k: _redact_pii(str(v)) if isinstance(v, str) else v for k, v in merge_variables.items()}

        payload = {
            "to": to_address,
            "from": from_address,
            "file": template_id,
            "merge_variables": merge_variables,
            "color": False,
            "double_sided": True,
            "address_placement": "top_first_page",
            "mail_type": "usps_first_class",
        }

        headers = {"Idempotency-Key": idempotency_key or str(uuid.uuid4())}

        async with httpx.AsyncClient(auth=(self._key(), "")) as client:
            resp = await client.post(f"{LOB_API_BASE}/letters", json=payload, headers=headers, timeout=30)
            if resp.status_code >= 400:
                raise LobApiError(resp.status_code, resp.text)
            result = resp.json()

        logger.info(
            "lob_letter_sent id=%s to_zip=%s template=%s",
            result.get("id"),
            to_address.get("address_zip"),
            template_id,
        )

        logger.debug("lob_letter_merge_vars statement_safe=%s", safe_vars)

        return result

    async def send_postcard(
        self,
        to_address: dict,
        from_address: dict,
        front_template_id: str,
        back_template_id: str,
        merge_variables: dict,
    ) -> dict:
        payload = {
            "to": to_address,
            "from": from_address,
            "front": front_template_id,
            "back": back_template_id,
            "merge_variables": merge_variables,
            "size": "4x6",
        }

        async with httpx.AsyncClient(auth=(self._key(), "")) as client:
            resp = await client.post(f"{LOB_API_BASE}/postcards", json=payload, timeout=30)
            if resp.status_code >= 400:
                raise LobApiError(resp.status_code, resp.text)
            return resp.json()

    async def create_address(self, address: dict) -> dict:
        async with httpx.AsyncClient(auth=(self._key(), "")) as client:
            resp = await client.post(f"{LOB_API_BASE}/addresses", json=address, timeout=30)
            if resp.status_code >= 400:
                raise LobApiError(resp.status_code, resp.text)
            return resp.json()

    async def verify_address(self, address: dict) -> dict:
        async with httpx.AsyncClient(auth=(self._key(), "")) as client:
            resp = await client.post(f"{LOB_API_BASE}/us_verifications", json=address, timeout=30)
            if resp.status_code >= 400:
                raise LobApiError(resp.status_code, resp.text)
            return resp.json()

    @staticmethod
    def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
        webhook_secret = os.environ.get("LOB_WEBHOOK_SECRET", secret)
        expected = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


async def send_statement_letter(
    *,
    pdf_bytes: bytes,
    outbound_sha256: str,
    statement_id: str,
    template_version: str,
    to_address: dict[str, Any],
    from_address: dict[str, Any],
) -> dict[str, Any]:
    """Send a billing statement letter via Lob.

    This helper exists because `core_app.api.statements_router` imports it at
    module import time. Keeping it here prevents import-time crashes that would
    otherwise take down the whole API (including /health).

    Implementation note:
    - We send the generated PDF as a data URI. If Lob rejects the payload, we
      raise `LobApiError` with the upstream response.
    """

    actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
    if actual_hash != outbound_sha256:
        raise ValueError(
            f"outbound_sha256 mismatch: expected {outbound_sha256}, got {actual_hash}"
        )

    api_key = _get_api_key()
    idempotency_key = f"statement-{statement_id}-{outbound_sha256[:16]}"

    # Data URI keeps this request self-contained (no prerequisite upload step).
    # Lob may reject this depending on account/API constraints; callers already
    # handle errors and surface a 5xx accordingly.
    file_data_uri = f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}"

    payload: dict[str, Any] = {
        "to": to_address,
        "from": from_address,
        "file": file_data_uri,
        "color": False,
        "double_sided": True,
        "address_placement": "top_first_page",
        "mail_type": "usps_first_class",
        "metadata": {
            "statement_id": statement_id,
            "template_version": template_version,
            "outbound_pdf_sha256": outbound_sha256,
        },
    }

    headers = {"Idempotency-Key": idempotency_key}

    async with httpx.AsyncClient(auth=(api_key, "")) as client:
        resp = await client.post(f"{LOB_API_BASE}/letters", json=payload, headers=headers, timeout=60)
        if resp.status_code >= 400:
            raise LobApiError(resp.status_code, resp.text)
        return resp.json()


def verify_lob_webhook_signature(
    *,
    raw_body: bytes,
    signature_header: str,
    timestamp_header: str,
    webhook_secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify Lob webhook signature.

    The expected signature is an HMAC-SHA256 hex digest over:

        f"{ts}.{base64(raw_body)}"

    and the timestamp must be within `tolerance_seconds` of current UTC time.

    This behavior matches our tests in `backend/tests/test_billing_integration.py`.
    """

    if not webhook_secret or not signature_header or not timestamp_header:
        return False

    try:
        ts = int(timestamp_header)
    except (TypeError, ValueError):
        return False

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if abs(now_ts - ts) > tolerance_seconds:
        return False

    signed = f"{ts}.{base64.b64encode(raw_body).decode()}"
    expected = hmac.new(webhook_secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
