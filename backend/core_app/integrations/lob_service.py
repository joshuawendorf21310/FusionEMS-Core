from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

LOB_API_BASE = "https://api.lob.com/v1"


class LobNotConfigured(Exception):
    pass


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
