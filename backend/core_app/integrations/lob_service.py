from __future__ import annotations

import hashlib
import hmac
import io
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests

from core_app.core.config import get_settings
from core_app.core.logging import configure_logging
import logging

logger = logging.getLogger(__name__)

LOB_API_BASE = "https://api.lob.com/v1"

# ── Config ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LobConfig:
    api_key: str
    webhook_secret: str = ""


class LobNotConfigured(Exception):
    pass


def _get_lob_config() -> LobConfig:
    settings = get_settings()
    key = getattr(settings, "lob_api_key", "")
    secret = getattr(settings, "lob_webhook_secret", "")
    if not key or key.startswith("REPLACE"):
        raise LobNotConfigured("LOB API key not configured")
    if not secret or secret.startswith("REPLACE"):
        raise LobNotConfigured("LOB webhook secret not configured")
    return LobConfig(api_key=key, webhook_secret=secret)


# ── Signature verification ────────────────────────────────────────────────────

def verify_lob_webhook_signature(
    *,
    raw_body: bytes,
    signature_header: str,
    timestamp_header: str,
    webhook_secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    """
    Lob HMAC-SHA256 signature verification.

    Lob signs:  timestamp + "." + base64(raw_body)
    Header:     Lob-Signature  (hex digest)
    Header:     Lob-Signature-Timestamp  (Unix seconds, str)

    Reference: https://docs.lob.com/#tag/Webhooks/Webhook-Security
    """
    if not webhook_secret or not signature_header or not timestamp_header:
        logger.warning("lob_sig_verify_missing_fields")
        return False
    try:
        ts = int(timestamp_header.strip())
    except ValueError:
        logger.warning("lob_sig_verify_bad_timestamp")
        return False

    now = int(time.time())
    if abs(now - ts) > tolerance_seconds:
        logger.warning("lob_sig_verify_timestamp_expired delta=%d", abs(now - ts))
        return False

    import base64
    signed_payload = f"{ts}.{base64.b64encode(raw_body).decode()}"
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


# ── Letter creation ───────────────────────────────────────────────────────────

def send_statement_letter(
    *,
    pdf_bytes: bytes,
    outbound_sha256: str,
    statement_id: str,
    template_version: str,
    to_address: dict[str, Any],
    from_address: dict[str, Any],
    description: str = "FusionEMS Medical Transport Statement",
    color: bool = True,
    double_sided: bool = True,
    mail_type: str = "usps_first_class",
) -> dict[str, Any]:
    """
    Upload PDF to Lob and create a letter.

    The EXACT pdf_bytes are hashed before upload and outbound_sha256 must match.
    Returns the full Lob letter response dict.
    """
    # Verify caller passed the correct hash BEFORE touching network
    computed = hashlib.sha256(pdf_bytes).hexdigest()
    if computed != outbound_sha256:
        raise ValueError(
            f"outbound_sha256 mismatch: caller={outbound_sha256[:16]} computed={computed[:16]}"
        )

    cfg = _get_lob_config()

    files = {"file": ("statement.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {
        "description": description,
        "to[name]":         to_address.get("name", ""),
        "to[address_line1]": to_address.get("line1", ""),
        "to[address_line2]": to_address.get("line2", ""),
        "to[address_city]":  to_address.get("city", ""),
        "to[address_state]": to_address.get("state", ""),
        "to[address_zip]":   to_address.get("zip", ""),
        "to[address_country]": to_address.get("country", "US"),
        "from[name]":          from_address.get("name", ""),
        "from[address_line1]": from_address.get("line1", ""),
        "from[address_line2]": from_address.get("line2", ""),
        "from[address_city]":  from_address.get("city", ""),
        "from[address_state]": from_address.get("state", ""),
        "from[address_zip]":   from_address.get("zip", ""),
        "from[address_country]": from_address.get("country", "US"),
        "color": str(color).lower(),
        "double_sided": str(double_sided).lower(),
        "mail_type": mail_type,
        "metadata[statement_id]": statement_id,
        "metadata[template_version]": template_version,
    }

    resp = requests.post(
        f"{LOB_API_BASE}/letters",
        auth=(cfg.api_key, ""),
        files=files,
        data=data,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.info(
        "lob_letter_created statement_id=%s lob_letter_id=%s outbound_sha256=%.16s",
        statement_id, result.get("id"), outbound_sha256,
    )
    return result


def get_letter(lob_letter_id: str) -> dict[str, Any]:
    cfg = _get_lob_config()
    resp = requests.get(
        f"{LOB_API_BASE}/letters/{lob_letter_id}",
        auth=(cfg.api_key, ""),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
