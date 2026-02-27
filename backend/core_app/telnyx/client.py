from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

TELNYX_API = "https://api.telnyx.com/v2"


class TelnyxNotConfigured(RuntimeError):
    pass


class TelnyxApiError(RuntimeError):
    def __init__(self, message: str, status_code: int = 0, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _headers(api_key: str) -> dict[str, str]:
    if not api_key:
        raise TelnyxNotConfigured("TELNYX_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _raise_for(resp: requests.Response, context: str) -> None:
    if resp.status_code >= 300:
        raise TelnyxApiError(
            f"{context} failed: HTTP {resp.status_code}",
            status_code=resp.status_code,
            body=resp.text[:400],
        )


# ── Call Control ──────────────────────────────────────────────────────────────

def call_answer(*, api_key: str, call_control_id: str) -> dict[str, Any]:
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/answer",
        headers=_headers(api_key),
        json={},
        timeout=10,
    )
    _raise_for(r, "call_answer")
    return r.json()


def call_gather_using_audio(
    *,
    api_key: str,
    call_control_id: str,
    audio_url: str,
    minimum_digits: int = 1,
    maximum_digits: int = 1,
    terminating_digit: str = "",
    timeout_millis: int = 8000,
    client_state: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "audio_url": audio_url,
        "minimum_digits": minimum_digits,
        "maximum_digits": maximum_digits,
        "timeout_millis": timeout_millis,
        "inter_digit_timeout_millis": 4000,
        "invalid_audio_url": audio_url,
    }
    if terminating_digit:
        payload["terminating_digit"] = terminating_digit
    if client_state:
        import base64
        payload["client_state"] = base64.b64encode(client_state.encode()).decode()
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/gather_using_audio",
        headers=_headers(api_key),
        json=payload,
        timeout=10,
    )
    _raise_for(r, "gather_using_audio")
    return r.json()


def call_playback_start(
    *,
    api_key: str,
    call_control_id: str,
    audio_url: str,
    loop: int = 1,
    client_state: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"audio_url": audio_url, "loop": loop}
    if client_state:
        import base64
        payload["client_state"] = base64.b64encode(client_state.encode()).decode()
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/playback_start",
        headers=_headers(api_key),
        json=payload,
        timeout=10,
    )
    _raise_for(r, "playback_start")
    return r.json()


def call_transfer(
    *,
    api_key: str,
    call_control_id: str,
    to: str,
    from_: str = "",
    client_state: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"to": to}
    if from_:
        payload["from"] = from_
    if client_state:
        import base64
        payload["client_state"] = base64.b64encode(client_state.encode()).decode()
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/transfer",
        headers=_headers(api_key),
        json=payload,
        timeout=10,
    )
    _raise_for(r, "call_transfer")
    return r.json()


def call_hangup(*, api_key: str, call_control_id: str) -> dict[str, Any]:
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/hangup",
        headers=_headers(api_key),
        json={},
        timeout=10,
    )
    _raise_for(r, "call_hangup")
    return r.json()


# ── Messaging ─────────────────────────────────────────────────────────────────

def send_sms(
    *,
    api_key: str,
    from_number: str,
    to_number: str,
    text: str,
    messaging_profile_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "from": from_number,
        "to": to_number,
        "text": text,
    }
    if messaging_profile_id:
        payload["messaging_profile_id"] = messaging_profile_id
    r = requests.post(
        f"{TELNYX_API}/messages",
        headers=_headers(api_key),
        json=payload,
        timeout=20,
    )
    _raise_for(r, "send_sms")
    return r.json()


# ── Media download ────────────────────────────────────────────────────────────

def download_media(*, api_key: str, media_url: str) -> bytes:
    r = requests.get(
        media_url,
        headers=_headers(api_key),
        timeout=60,
        stream=True,
    )
    _raise_for(r, "download_media")
    chunks = []
    for chunk in r.iter_content(chunk_size=65536):
        if chunk:
            chunks.append(chunk)
    return b"".join(chunks)
