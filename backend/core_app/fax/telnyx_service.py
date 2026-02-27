from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class TelnyxNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class TelnyxConfig:
    api_key: str
    messaging_profile_id: str | None = None


TELNYX_API = "https://api.telnyx.com/v2"


def _headers(cfg: TelnyxConfig) -> dict[str, str]:
    if not cfg.api_key:
        raise TelnyxNotConfigured("telnyx_api_key_missing")
    return {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"}


def send_sms(*, cfg: TelnyxConfig, from_number: str, to_number: str, text: str) -> dict[str, Any]:
    payload = {
        "from": from_number,
        "to": to_number,
        "text": text,
    }
    if cfg.messaging_profile_id:
        payload["messaging_profile_id"] = cfg.messaging_profile_id
    r = requests.post(f"{TELNYX_API}/messages", headers=_headers(cfg), json=payload, timeout=20)
    if r.status_code >= 300:
        raise TelnyxNotConfigured(f"telnyx_send_sms_failed:{r.status_code}:{r.text[:200]}")
    return r.json()


def download_media(*, cfg: TelnyxConfig, media_url: str) -> bytes:
    r = requests.get(media_url, headers=_headers(cfg), timeout=60)
    if r.status_code >= 300:
        raise TelnyxNotConfigured(f"telnyx_download_media_failed:{r.status_code}:{r.text[:200]}")
    return r.content
