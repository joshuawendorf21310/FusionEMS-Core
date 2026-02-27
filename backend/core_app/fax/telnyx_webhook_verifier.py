from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Optional


def verify_telnyx_signature(
    raw_body: bytes,
    telnyx_signature_ed25519: Optional[str],
    telnyx_timestamp: Optional[str],
    webhook_secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    if not telnyx_timestamp:
        return False
    try:
        ts = int(telnyx_timestamp)
    except (ValueError, TypeError):
        return False
    if abs(time.time() - ts) > tolerance_seconds:
        return False
    if not telnyx_signature_ed25519:
        return False
    signed = f"{ts}|{raw_body.decode('utf-8', errors='replace')}"
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        signed.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    try:
        actual = base64.b64decode(telnyx_signature_ed25519).hex()
    except Exception:
        actual = telnyx_signature_ed25519
    return hmac.compare_digest(expected, actual)
