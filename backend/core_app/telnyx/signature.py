from __future__ import annotations

import base64
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key


def verify_telnyx_webhook(
    *,
    raw_body: bytes,
    signature_ed25519: str | None,
    timestamp: str | None,
    public_key_base64: str,
    tolerance_seconds: int = 300,
) -> bool:
    """
    Verify a Telnyx webhook Ed25519 signature.

    Telnyx signs:  "{timestamp}|{raw_request_body_string}"
    Header:        telnyx-signature-ed25519  (base64-encoded Ed25519 sig over the signed payload)
    Header:        telnyx-timestamp          (unix epoch seconds string)

    The public key is the base64-encoded DER-format Ed25519 public key from the
    Telnyx portal (TELNYX_PUBLIC_KEY env var).
    """
    if not timestamp:
        return False
    if not signature_ed25519:
        return False
    if not public_key_base64:
        return False

    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - ts) > tolerance_seconds:
        return False

    signed_payload = f"{timestamp}|{raw_body.decode('utf-8', errors='replace')}"

    try:
        sig_bytes = base64.b64decode(signature_ed25519)
    except Exception:
        return False

    try:
        key_der = base64.b64decode(public_key_base64)
        public_key: Ed25519PublicKey = load_der_public_key(key_der)  # type: ignore[assignment]
        public_key.verify(sig_bytes, signed_payload.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, TypeError, Exception):
        return False
