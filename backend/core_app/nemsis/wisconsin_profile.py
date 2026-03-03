from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WisconsinStateRule:
    rule_id: str
    field_path: str
    description: str
    severity: str
    check_fn_name: str


@dataclass
class WisconsinProfileResult:
    passed: bool
    rules_checked: int = 0
    rules_passed: int = 0
    violations: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "rules_checked": self.rules_checked,
            "rules_passed": self.rules_passed,
            "violations": self.violations,
            "warnings": self.warnings,
        }


WI_STATE_RULES: list[WisconsinStateRule] = [
    WisconsinStateRule(
        rule_id="WI-001",
        field_path="eTimes.06",
        description="Unit Arrived on Scene date/time is required for all 911 responses",
        severity="error",
        check_fn_name="_check_etimes_06",
    ),
    WisconsinStateRule(
        rule_id="WI-002",
        field_path="eTimes.07",
        description="Arrived at Patient date/time is required",
        severity="error",
        check_fn_name="_check_etimes_07",
    ),
    WisconsinStateRule(
        rule_id="WI-003",
        field_path="eResponse.13",
        description="Unit Transport and Equipment Capability must use WI-accepted codes",
        severity="error",
        check_fn_name="_check_eresponse_13",
    ),
    WisconsinStateRule(
        rule_id="WI-004",
        field_path="eResponse.23",
        description="Response Mode to Scene is required",
        severity="error",
        check_fn_name="_check_eresponse_23",
    ),
    WisconsinStateRule(
        rule_id="WI-005",
        field_path="eSituation.11",
        description="Provider Primary Impression must be a valid ICD-10 code",
        severity="error",
        check_fn_name="_check_esituation_11",
    ),
    WisconsinStateRule(
        rule_id="WI-006",
        field_path="ePatient.13",
        description="Patient Gender must use approved NEMSIS code set",
        severity="error",
        check_fn_name="_check_epatient_13",
    ),
    WisconsinStateRule(
        rule_id="WI-007",
        field_path="eDisposition.12",
        description="Incident/Patient Disposition is required",
        severity="error",
        check_fn_name="_check_edisposition_12",
    ),
    WisconsinStateRule(
        rule_id="WI-008",
        field_path="eScene.09",
        description="Incident Location Type is required for all calls",
        severity="warning",
        check_fn_name="_check_escene_09",
    ),
    WisconsinStateRule(
        rule_id="WI-009",
        field_path="eRecord.SoftwareApplicationGroup",
        description="Software application info is required for WARDS submission",
        severity="warning",
        check_fn_name="_check_software_info",
    ),
]

WI_GENDER_CODES = {"9906001", "9906003", "9906005", "9906007", "9906009"}
WI_DISPOSITION_CODES = {
    "4212001", "4212003", "4212005", "4212007", "4212009",
    "4212011", "4212013", "4212015", "4212017", "4212019",
    "4212021", "4212023", "4212025", "4212027", "4212029",
    "4212031", "4212033", "4212035",
}


class WisconsinProfile:
    def __init__(self):
        self._rules = WI_STATE_RULES

    def validate(self, record: dict) -> WisconsinProfileResult:
        result = WisconsinProfileResult(passed=True)

        for rule in self._rules:
            result.rules_checked += 1
            check_fn = getattr(self, rule.check_fn_name, None)
            if check_fn is None:
                continue
            issue = check_fn(record)
            if issue is None:
                result.rules_passed += 1
            else:
                entry = {
                    "rule_id": rule.rule_id,
                    "field_path": rule.field_path,
                    "description": rule.description,
                    "detail": issue,
                }
                if rule.severity == "error":
                    result.violations.append(entry)
                    result.passed = False
                else:
                    result.warnings.append(entry)
                    result.rules_passed += 1

        return result

    def _get_field(self, record: dict, path: str) -> Optional[str]:
        parts = path.split(".")
        current = record
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return str(current) if current is not None else None

    def _check_etimes_06(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eTimes.06")
        if not val:
            return "Unit Arrived on Scene date/time is missing"
        return None

    def _check_etimes_07(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eTimes.07")
        if not val:
            return "Arrived at Patient date/time is missing"
        return None

    def _check_eresponse_13(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eResponse.13")
        if not val:
            return "Unit Transport and Equipment Capability is missing"
        return None

    def _check_eresponse_23(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eResponse.23")
        if not val:
            return "Response Mode to Scene is missing"
        return None

    def _check_esituation_11(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eSituation.11")
        if not val:
            return "Provider Primary Impression is missing"
        return None

    def _check_epatient_13(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "ePatient.13")
        if not val:
            return "Patient Gender is missing"
        if val not in WI_GENDER_CODES:
            return f"Patient Gender code '{val}' is not in WI-accepted code set"
        return None

    def _check_edisposition_12(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eDisposition.12")
        if not val:
            return "Incident/Patient Disposition is missing"
        if val not in WI_DISPOSITION_CODES:
            return f"Disposition code '{val}' is not in WI-accepted code set"
        return None

    def _check_escene_09(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eScene.09")
        if not val:
            return "Incident Location Type is missing"
        return None

    def _check_software_info(self, record: dict) -> Optional[str]:
        val = self._get_field(record, "eRecord.SoftwareApplicationGroup")
        if not val:
            return "Software application group info missing for WARDS submission"
        return None

    @staticmethod
    def wards_submission_adapter(validated_xml: str) -> dict:
        return {
            "format": "NEMSIS_v3.5.1",
            "state": "WI",
            "target_system": "WARDS_Elite",
            "payload": validated_xml,
            "transport": "SFTP",
            "notes": "Wisconsin state submission via WARDS Elite linkage",
        }
