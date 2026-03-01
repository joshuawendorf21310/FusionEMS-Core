from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher


class NERISValidator:
    def __init__(self, db, publisher: EventPublisher, tenant_id: uuid.UUID) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id

    def _get_rules(self, pack_id: uuid.UUID, entity_type: str) -> dict[str, Any] | None:
        all_rules = self.svc.repo("neris_compiled_rules").list(tenant_id=self.tenant_id, limit=50)
        for r in all_rules:
            rd = r.get("data") or {}
            if rd.get("pack_id") == str(pack_id) and rd.get("entity_type") == entity_type:
                return rd.get("rules_json")
        return None

    def validate(self, pack_id: uuid.UUID, entity_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rules = self._get_rules(pack_id, entity_type)
        if not rules:
            return [{"severity": "warning", "entity_type": entity_type, "rule_id": "no_rules", "path": "", "field_label": "", "ui_section": "System", "message": "No compiled rules found for this pack. Import and compile the pack first.", "suggested_fix": "Go to Compliance Studio and compile the active NERIS pack."}]

        issues: list[dict[str, Any]] = []
        value_sets = rules.get("value_sets", {})

        for section in rules.get("sections", []):
            sec_label = section.get("label", "")
            for field in section.get("fields", []):
                path = field.get("path", "")
                label = field.get("label", path)
                required = field.get("required", False)
                ftype = field.get("type", "string")
                vs_code = field.get("value_set")

                if "[]" in path:
                    array_path = path.split("[]")[0].rstrip(".")
                    array_val = _get_path(payload, array_path)
                    if required and (array_val is None or array_val == [] or not isinstance(array_val, list) or len(array_val) == 0):
                        issues.append({
                            "severity": "error",
                            "entity_type": entity_type,
                            "rule_id": f"{array_path}.required",
                            "path": array_path,
                            "field_label": label,
                            "ui_section": sec_label,
                            "message": f"At least one {label} entry is required.",
                            "suggested_fix": f"Add at least one {label} record.",
                        })
                    continue

                value = _get_path(payload, path)

                if required and (value is None or value == "" or value == []):
                    issues.append({
                        "severity": "error",
                        "entity_type": entity_type,
                        "rule_id": f"{path}.required",
                        "path": path,
                        "field_label": label,
                        "ui_section": sec_label,
                        "message": f"{label} is required.",
                        "suggested_fix": f"Please provide a value for {label}.",
                    })
                    continue

                if value is None:
                    continue

                if ftype == "datetime" and isinstance(value, str):
                    try:
                        datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        issues.append({
                            "severity": "error",
                            "entity_type": entity_type,
                            "rule_id": f"{path}.invalid_datetime",
                            "path": path,
                            "field_label": label,
                            "ui_section": sec_label,
                            "message": f"{label} must be a valid ISO 8601 datetime.",
                            "suggested_fix": "Use format: YYYY-MM-DDTHH:MM:SS",
                        })

                if ftype == "email" and isinstance(value, str) and not re.match(r"[^@]+@[^@]+\.[^@]+", value):
                    issues.append({
                            "severity": "error",
                            "entity_type": entity_type,
                            "rule_id": f"{path}.invalid_email",
                            "path": path,
                            "field_label": label,
                            "ui_section": sec_label,
                            "message": f"{label} must be a valid email address.",
                            "suggested_fix": "Enter a valid email address.",
                        })

                if ftype == "integer":
                    try:
                        int(value)
                    except (TypeError, ValueError):
                        issues.append({
                            "severity": "error",
                            "entity_type": entity_type,
                            "rule_id": f"{path}.invalid_integer",
                            "path": path,
                            "field_label": label,
                            "ui_section": sec_label,
                            "message": f"{label} must be a whole number.",
                            "suggested_fix": "Enter a whole number (e.g. 0, 1, 2).",
                        })

                if vs_code and isinstance(value, str):
                    allowed = value_sets.get(vs_code, {}).get("allowed", [])
                    if allowed and value not in allowed:
                        issues.append({
                            "severity": "error",
                            "entity_type": entity_type,
                            "rule_id": f"{path}.invalid_value",
                            "path": path,
                            "field_label": label,
                            "ui_section": sec_label,
                            "message": f"'{value}' is not a valid value for {label}. Allowed: {', '.join(allowed[:10])}{'...' if len(allowed) > 10 else ''}",
                            "suggested_fix": f"Select one of the allowed values for {label}.",
                        })

        for constraint in rules.get("constraints", []):
            ctype = constraint.get("type")
            severity = constraint.get("severity", "error")
            message = constraint.get("message", "")
            rule_id = constraint.get("id", "")

            if ctype == "compare":
                a_path = constraint.get("a", "")
                b_path = constraint.get("b", "")
                op = constraint.get("op", ">=")
                a_val = _get_path(payload, a_path)
                b_val = _get_path(payload, b_path)
                if a_val and b_val and isinstance(a_val, str) and isinstance(b_val, str):
                    try:
                        a_dt = datetime.fromisoformat(a_val.replace("Z", "+00:00"))
                        b_dt = datetime.fromisoformat(b_val.replace("Z", "+00:00"))
                        violated = False
                        if op == ">=" and not (a_dt >= b_dt) or op == "<=" and not (a_dt <= b_dt) or op == ">" and not (a_dt > b_dt):
                            violated = True
                        if violated:
                            issues.append({
                                "severity": severity,
                                "entity_type": entity_type,
                                "rule_id": rule_id,
                                "path": a_path,
                                "field_label": a_path,
                                "ui_section": "Incident Basics",
                                "message": message,
                                "suggested_fix": "Check the time fields.",
                            })
                    except Exception:
                        pass

        return issues


def _get_path(payload: dict, path: str) -> Any:
    """Dot-notation path resolver. Handles top-level dot paths only (no arrays)."""
    parts = path.split(".")
    current = payload
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
