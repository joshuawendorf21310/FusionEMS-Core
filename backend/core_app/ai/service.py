from __future__ import annotations

import hashlib
import time
from typing import Any

from openai import OpenAI

from core_app.core.config import get_settings


class AiService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI API key not configured")
        self.client = OpenAI(api_key=settings.openai_api_key)

    def chat(
        self, *, system: str, user: str, max_tokens: int | None = None
    ) -> tuple[str, dict[str, Any]]:
        get_settings()
        start = time.time()
        create_kwargs: dict[str, Any] = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        resp = self.client.chat.completions.create(**create_kwargs)
        content = resp.choices[0].message.content or ""
        usage = resp.usage.model_dump() if resp.usage else {}
        meta = {
            "model": resp.model,
            "usage": usage,
            "latency_ms": int((time.time() - start) * 1000),
        }
        return content, meta


def hash_input(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
