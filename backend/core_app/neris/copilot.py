from __future__ import annotations

import json
import uuid
from typing import Any

from core_app.ai.service import AiService


SYSTEM_PROMPT = """You are a NERIS (National Emergency Response Information System) compliance expert for Wisconsin fire departments. You explain validation errors in plain English and generate structured remediation actions. Always respond with valid JSON only, no markdown.

Output schema:
{
  "summary": "Brief overall assessment",
  "actions": [
    {
      "type": "UI_FIELD" | "CONFIGURATION" | "TRAINING",
      "path": "field.path or null",
      "ui_section": "section name or null",
      "instruction": "What to do"
    }
  ],
  "confidence": 0.0 to 1.0
}"""


class NERISCopilot:
    def __init__(self) -> None:
        self.ai = AiService()

    def explain_issues(self, issues: list[dict[str, Any]], context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not issues:
            return {"summary": "No validation issues found. Your data is ready for export.", "actions": [], "confidence": 1.0}

        ctx = context or {}
        state = ctx.get("state", "WI")
        pack_id = ctx.get("pack_id", "")

        user_prompt = f"""Wisconsin NERIS validation issues (state={state}, pack_id={pack_id}):

{json.dumps(issues, indent=2)}

Explain each issue in plain English for a fire department administrator and provide specific UI actions to fix them."""

        try:
            content, _ = self.ai.chat(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=2048)
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError("not a dict")
            return result
        except Exception as exc:
            return {
                "summary": f"Unable to generate AI explanation: {exc}. Please review the issues list manually.",
                "actions": [
                    {
                        "type": "UI_FIELD",
                        "path": issue.get("path"),
                        "ui_section": issue.get("ui_section"),
                        "instruction": issue.get("suggested_fix") or issue.get("message"),
                    }
                    for issue in issues
                ],
                "confidence": 0.5,
            }
