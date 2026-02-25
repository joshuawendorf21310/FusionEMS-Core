from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from core_app.services.documents_service import create_docx, create_xlsx, create_invoice_pdf

DATA_DIR = Path(os.getenv("FQ_DATA_DIR", Path(__file__).resolve().parents[2] / ".data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "founder_settings.json"

def _load() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save(data: dict[str, Any]) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def save_founder_settings(founder_email: str, keys: dict[str, Any]) -> None:
    data = _load()
    data["founder_email"] = founder_email
    # Minimal at-rest protection: base64 encode to avoid plain accidental logs.
    # Production should use KMS envelope encryption.
    safe_keys = {k: base64.b64encode((v or "").encode("utf-8")).decode("utf-8") for k, v in keys.items()}
    data["keys_b64"] = safe_keys
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save(data)

def get_founder_status() -> dict[str, Any]:
    data = _load()
    keys_b64 = data.get("keys_b64", {})
    def present(k: str) -> bool:
        v = keys_b64.get(k)
        return bool(v and base64.b64decode(v.encode("utf-8")).decode("utf-8").strip())
    modules = [
        {"module":"OpenAI", "ok": present("openai_api_key"), "detail": "AI operations & copilots"},
        {"module":"Telnyx", "ok": present("telnyx_api_key"), "detail": "Voice/SMS/Fax webhooks"},
        {"module":"Stripe", "ok": present("stripe_secret_key"), "detail": "Payments (optional)"},
        {"module":"LOB", "ok": present("lob_api_key"), "detail": "Letters/printing (optional)"},
        {"module":"Email (SES)", "ok": present("ses_from_email"), "detail": "Outbound billing email"},
    ]
    return {
        "founderEmail": data.get("founder_email", ""),
        "modules": modules,
        "realtime": {"connected": True},
        "updatedAt": data.get("updated_at"),
    }

def create_document_for_founder(kind: str, title: str, body: str) -> dict[str, str]:
    out_dir = DATA_DIR / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    if kind == "word":
        path = create_docx(out_dir, title, body)
    elif kind == "excel":
        path = create_xlsx(out_dir, title, body)
    elif kind == "invoice":
        path = create_invoice_pdf(out_dir, title, body)
    else:
        raise ValueError("Unsupported kind")
    # Local dev: direct download URL served by backend static route
    return {"download_url": f"/api/v1/files/{path.name}"}
