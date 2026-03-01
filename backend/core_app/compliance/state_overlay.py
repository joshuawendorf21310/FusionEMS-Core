from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationRule:
    field_path: str
    rule_type: str
    message: str
    severity: str = "error"
    condition: Callable[[dict[str, Any]], bool] | None = None


@dataclass
class StateProfile:
    state_code: str
    state_name: str
    nemsis_version: str
    additional_required_fields: list[str]
    rules: list[ValidationRule]
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self, incident_data: dict[str, Any]) -> list[dict[str, Any]]:
        violations = []
        for rule in self.rules:
            if rule.condition and not rule.condition(incident_data):
                continue
            val = _get_nested(incident_data, rule.field_path)
            if rule.rule_type == "required" and not val or rule.rule_type == "not_empty" and val is not None and str(val).strip() == "":
                violations.append({
                    "field": rule.field_path,
                    "severity": rule.severity,
                    "message": rule.message,
                    "rule_type": rule.rule_type,
                })
        return violations


def _get_nested(data: dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


WISCONSIN_PROFILE = StateProfile(
    state_code="WI",
    state_name="Wisconsin",
    nemsis_version="3.5.0",
    additional_required_fields=[
        "incident_number",
        "dispatch_time",
        "arrived_scene_time",
        "patient_contact_time",
        "arrived_destination_time",
        "patient_disposition_code",
        "primary_impression_code",
        "transport_mode",
        "unit_number",
    ],
    rules=[
        ValidationRule(
            field_path="incident_number",
            rule_type="required",
            message="Wisconsin requires incident number (eIncident.01)",
            severity="error",
        ),
        ValidationRule(
            field_path="dispatch_time",
            rule_type="required",
            message="Wisconsin requires dispatch time (eTimes.01)",
            severity="error",
        ),
        ValidationRule(
            field_path="arrived_scene_time",
            rule_type="required",
            message="Wisconsin requires scene arrival time (eTimes.06)",
            severity="error",
        ),
        ValidationRule(
            field_path="patient_contact_time",
            rule_type="required",
            message="Wisconsin requires patient contact time (eTimes.07)",
            severity="error",
        ),
        ValidationRule(
            field_path="arrived_destination_time",
            rule_type="required",
            message="Wisconsin requires destination arrival time (eTimes.11)",
            severity="warning",
            condition=lambda d: d.get("patient_disposition_code") == "4227001",
        ),
        ValidationRule(
            field_path="unit_number",
            rule_type="required",
            message="Wisconsin requires responding unit identifier (eResponse.13)",
            severity="error",
        ),
        ValidationRule(
            field_path="primary_impression_code",
            rule_type="required",
            message="Wisconsin requires primary impression (eSituation.11)",
            severity="error",
        ),
        ValidationRule(
            field_path="transport_mode",
            rule_type="required",
            message="Wisconsin requires transport mode (eResponse.23)",
            severity="warning",
        ),
    ],
    metadata={
        "state_submission_url": "https://www.dhs.wisconsin.gov/ems/data/index.htm",
        "contact": "WI DHS EMS Section",
        "last_updated": "2024-01-01",
    },
)

STATE_PROFILES: dict[str, StateProfile] = {
    "WI": WISCONSIN_PROFILE,
}


def get_state_profile(state_code: str) -> StateProfile | None:
    return STATE_PROFILES.get(state_code.upper())


def validate_with_state_overlay(
    incident_data: dict[str, Any],
    state_code: str = "WI",
) -> dict[str, Any]:
    profile = get_state_profile(state_code)
    if not profile:
        return {"state_code": state_code, "violations": [], "note": "No profile for state"}

    violations = profile.validate(incident_data)
    errors = [v for v in violations if v["severity"] == "error"]
    warnings = [v for v in violations if v["severity"] == "warning"]
    return {
        "state_code": state_code,
        "state_name": profile.state_name,
        "nemsis_version": profile.nemsis_version,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_violations": len(violations),
    }
