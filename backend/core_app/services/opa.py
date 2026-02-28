from __future__ import annotations

import requests
from typing import Any

from core_app.core.config import get_settings


class OpaError(Exception):
    pass


def opa_enabled() -> bool:
    return bool(get_settings().opa_url)


def check_policy(input_doc: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.opa_url:
        return True  # fallback to app RBAC if OPA not configured
    url = settings.opa_url.rstrip("/") + "/" + settings.opa_policy_path.lstrip("/")
    try:
        resp = requests.post(url, json={"input": input_doc}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return bool(data.get("result", False))
    except Exception as exc:
        raise OpaError(str(exc)) from exc
