from __future__ import annotations

import contextlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

try:
    from lxml import etree as lxml_etree

    _LXML_AVAILABLE = True
except ImportError:
    _LXML_AVAILABLE = False

ELEMENT_UI_MAP: dict[str, dict[str, str]] = {
    "eRecord.01": {"label": "PCR Report Number", "section": "Record → Header"},
    "eIncident.01": {"label": "Incident Number", "section": "Incident → Details"},
    "eTimes.01": {"label": "PSAP Call Time", "section": "Times → Dispatch"},
    "eTimes.03": {"label": "Unit Notified Time", "section": "Times → Dispatch"},
    "eTimes.06": {"label": "Arrived Scene Time", "section": "Times → Scene"},
    "eTimes.07": {"label": "Patient Contact Time", "section": "Times → Scene"},
    "eTimes.11": {"label": "Arrived Destination Time", "section": "Times → Transport"},
    "ePatient.02": {"label": "Patient DOB", "section": "Patient → Demographics"},
    "ePatient.03": {"label": "Patient Last Name", "section": "Patient → Demographics"},
    "ePatient.04": {"label": "Patient First Name", "section": "Patient → Demographics"},
    "ePatient.13": {"label": "Patient Gender", "section": "Patient → Demographics"},
    "ePatient.17": {"label": "Patient Race", "section": "Patient → Demographics"},
    "eResponse.13": {"label": "Unit Call Sign", "section": "Response → Unit"},
    "eResponse.23": {"label": "Transport Mode", "section": "Response → Transport"},
    "eSituation.11": {"label": "Primary Impression", "section": "Situation → Assessment"},
    "eVitals": {"label": "Vital Signs", "section": "Vitals"},
    "eNarrative.01": {"label": "Narrative", "section": "Narrative"},
    "eDisposition.27": {"label": "Final Patient Acuity", "section": "Disposition"},
    "dAgency.04": {"label": "Agency State", "section": "Agency → Demographics"},
}

VALID_GENDER_CODES = {"9906001", "9906003", "9906009"}
VALID_ACUITY_CODES = {"9902001", "9902003", "9902005", "9902007", "9902009"}
_ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)?$")

NEMSIS_NS = "http://www.nemsis.org"


def _ui_info(element_id: str) -> tuple[str, str]:
    entry = ELEMENT_UI_MAP.get(element_id, {})
    return entry.get("section", "Unknown"), entry.get("label", element_id)


def _find_text(root: ET.Element, local_name: str) -> str | None:
    for elem in root.iter():
        tag = elem.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag == local_name:
            return (elem.text or "").strip() or None
    return None


def _find_all(root: ET.Element, local_name: str) -> list[ET.Element]:
    result = []
    for elem in root.iter():
        tag = elem.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag == local_name:
            result.append(elem)
    return result


@dataclass
class ValidationIssue:
    severity: str
    stage: str
    rule_id: str
    element_id: str
    xpath: str
    ui_section: str
    plain_message: str
    technical_message: str
    rule_source: str
    fix_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "stage": self.stage,
            "rule_id": self.rule_id,
            "element_id": self.element_id,
            "xpath": self.xpath,
            "ui_section": self.ui_section,
            "plain_message": self.plain_message,
            "technical_message": self.technical_message,
            "rule_source": self.rule_source,
            "fix_hint": self.fix_hint,
        }


@dataclass
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    stage_results: dict[str, Any] = field(default_factory=dict)
    xml_bytes: bytes | None = None
    validated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "stage_results": self.stage_results,
            "validated_at": self.validated_at,
        }


def _make_issue(
    severity: str,
    stage: str,
    rule_id: str,
    element_id: str,
    plain_message: str,
    technical_message: str,
    rule_source: str,
    fix_hint: str,
) -> ValidationIssue:
    section, label = _ui_info(element_id)
    xpath = f"/EMSDataSet/PatientCareReport/{element_id.replace('.', '/')}"
    return ValidationIssue(
        severity=severity,
        stage=stage,
        rule_id=rule_id,
        element_id=element_id,
        xpath=xpath,
        ui_section=section,
        plain_message=plain_message,
        technical_message=technical_message,
        rule_source=rule_source,
        fix_hint=fix_hint,
    )


class NEMSISValidator:
    def validate_xml_bytes(self, xml_bytes: bytes, state_code: str = "WI") -> ValidationResult:
        all_issues: list[ValidationIssue] = []
        stage_results: dict[str, Any] = {}
        root: ET.Element | None = None

        xsd_issues = self._stage_xsd(xml_bytes)
        all_issues.extend(xsd_issues)
        stage_results["xsd"] = {
            "passed": not any(i.severity == "error" for i in xsd_issues),
            "issue_count": len(xsd_issues),
        }

        with contextlib.suppress(ET.ParseError):
            root = ET.fromstring(xml_bytes)

        if root is not None:
            nat_issues = self._stage_national_schematron(root)
            all_issues.extend(nat_issues)
            stage_results["national_schematron"] = {
                "passed": not any(i.severity == "error" for i in nat_issues),
                "issue_count": len(nat_issues),
            }

            if state_code.upper() == "WI":
                wi_issues = self._stage_wi_schematron(root)
                all_issues.extend(wi_issues)
                stage_results["wi_schematron"] = {
                    "passed": not any(i.severity == "error" for i in wi_issues),
                    "issue_count": len(wi_issues),
                }

                wi_state_issues = self._stage_wi_state(root)
                all_issues.extend(wi_state_issues)
                stage_results["wi_state"] = {
                    "passed": not any(i.severity == "error" for i in wi_state_issues),
                    "issue_count": len(wi_state_issues),
                }
        else:
            for stage in ("national_schematron", "wi_schematron", "wi_state"):
                stage_results[stage] = {"passed": False, "issue_count": 0, "skipped": True}

        valid = not any(i.severity == "error" for i in all_issues)
        return ValidationResult(
            valid=valid,
            issues=all_issues,
            stage_results=stage_results,
            xml_bytes=xml_bytes,
            validated_at=datetime.now(UTC).isoformat(),
        )

    def _stage_xsd(self, xml_bytes: bytes) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if _LXML_AVAILABLE:
            try:
                lxml_etree.fromstring(xml_bytes)
            except lxml_etree.XMLSyntaxError as exc:
                for err in exc.error_log:
                    issues.append(
                        _make_issue(
                            severity="error",
                            stage="xsd",
                            rule_id="XSD-001",
                            element_id="structure",
                            plain_message=f"XML syntax error at line {err.line}: {err.message}",
                            technical_message=str(err),
                            rule_source="Structure",
                            fix_hint="Fix XML syntax near the indicated line.",
                        )
                    )
                return issues
        else:
            try:
                ET.fromstring(xml_bytes)
            except ET.ParseError as exc:
                issues.append(
                    _make_issue(
                        severity="error",
                        stage="xsd",
                        rule_id="XSD-001",
                        element_id="structure",
                        plain_message=f"XML parse error: {exc}",
                        technical_message=str(exc),
                        rule_source="Structure",
                        fix_hint="Fix XML syntax error in the document.",
                    )
                )
                return issues

        preview = xml_bytes[:500].decode(errors="ignore")
        if "EMSDataSet" not in preview and "DEMDataSet" not in preview:
            issues.append(
                _make_issue(
                    severity="warning",
                    stage="xsd",
                    rule_id="XSD-002",
                    element_id="structure",
                    plain_message="Root element does not appear to be a NEMSIS EMSDataSet or DEMDataSet.",
                    technical_message="Neither 'EMSDataSet' nor 'DEMDataSet' found in first 500 bytes.",
                    rule_source="Structure",
                    fix_hint="Ensure the root element is <EMSDataSet> or <DEMDataSet> with the correct NEMSIS namespace.",
                )
            )

        return issues

    def _stage_national_schematron(self, root: ET.Element) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        checks = [
            (
                "eRecord.01",
                "NEMSIS-001",
                "PCR Report Number (eRecord.01) is missing or empty.",
                "eRecord.01 element not found or has no text content.",
                "National NEMSIS",
                "Add a unique PCR report number to eRecord.01.",
            ),
            (
                "eIncident.01",
                "NEMSIS-002",
                "Incident Number (eIncident.01) is missing or empty.",
                "eIncident.01 element not found.",
                "National NEMSIS",
                "Populate eIncident.01 with the incident number.",
            ),
            (
                "eTimes.01",
                "NEMSIS-003",
                "PSAP Call Time (eTimes.01) is required but missing.",
                "eTimes.01 element not found.",
                "National NEMSIS",
                "Set eTimes.01 to the PSAP call date/time in ISO 8601 format.",
            ),
            (
                "eTimes.03",
                "NEMSIS-004",
                "Unit Notified Time (eTimes.03) is required but missing.",
                "eTimes.03 element not found.",
                "National NEMSIS",
                "Set eTimes.03 to the unit notified date/time.",
            ),
            (
                "eNarrative.01",
                "NEMSIS-008",
                "Narrative (eNarrative.01) is required but missing.",
                "eNarrative.01 element not found.",
                "National NEMSIS",
                "Add a patient care narrative to eNarrative.01.",
            ),
            (
                "eDisposition.27",
                "NEMSIS-009",
                "Final Patient Acuity (eDisposition.27) is required but missing.",
                "eDisposition.27 element not found.",
                "National NEMSIS",
                "Set eDisposition.27 to the final patient acuity code.",
            ),
        ]

        for element_id, rule_id, plain_msg, tech_msg, source, hint in checks:
            element_id.split(".")[-1] if "." in element_id else element_id
            parent_local = element_id.split(".")[0] if "." in element_id else element_id
            val = _find_text(root, parent_local + "." + (element_id.split(".")[-1]))
            if val is None:
                issues.append(
                    _make_issue(
                        "error",
                        "national_schematron",
                        rule_id,
                        element_id,
                        plain_msg,
                        tech_msg,
                        source,
                        hint,
                    )
                )

        epatient_elems = _find_all(root, "ePatient")
        if not epatient_elems:
            issues.append(
                _make_issue(
                    severity="error",
                    stage="national_schematron",
                    rule_id="NEMSIS-005",
                    element_id="ePatient",
                    plain_message="The ePatient section is missing from this PCR.",
                    technical_message="No ePatient element found in document.",
                    rule_source="National NEMSIS",
                    fix_hint="Include the ePatient section with at least the required demographic fields.",
                )
            )

        vital_groups = _find_all(root, "eVitals")
        if not vital_groups:
            issues.append(
                _make_issue(
                    severity="error",
                    stage="national_schematron",
                    rule_id="NEMSIS-007",
                    element_id="eVitals",
                    plain_message="At least one set of vital signs (eVitals) is required.",
                    technical_message="No eVitals element found in document.",
                    rule_source="National NEMSIS",
                    fix_hint="Add at least one VitalGroup/eVitals section with vital sign measurements.",
                )
            )

        return issues

    def _stage_wi_schematron(self, root: ET.Element) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        wi_checks = [
            (
                "eTimes.06",
                "WI-001",
                "Wisconsin requires Arrived Scene Time (eTimes.06).",
                "eTimes.06 not found.",
                "Set eTimes.06 to the unit arrived on scene date/time.",
            ),
            (
                "eTimes.07",
                "WI-002",
                "Wisconsin requires Patient Contact Time (eTimes.07).",
                "eTimes.07 not found.",
                "Set eTimes.07 to the patient contact date/time.",
            ),
            (
                "eResponse.13",
                "WI-003",
                "Wisconsin requires Unit Call Sign (eResponse.13).",
                "eResponse.13 not found.",
                "Populate eResponse.13 with the unit's call sign.",
            ),
            (
                "eSituation.11",
                "WI-004",
                "Wisconsin requires Primary Impression (eSituation.11).",
                "eSituation.11 not found.",
                "Select a provider primary impression code for eSituation.11.",
            ),
            (
                "eResponse.23",
                "WI-005",
                "Wisconsin requires Transport Mode (eResponse.23).",
                "eResponse.23 not found.",
                "Set eResponse.23 to the appropriate transport mode code.",
            ),
        ]

        for element_id, rule_id, plain_msg, tech_msg, hint in wi_checks:
            val = _find_text(root, element_id)
            if val is None:
                issues.append(
                    _make_issue(
                        "error",
                        "wi_schematron",
                        rule_id,
                        element_id,
                        plain_msg,
                        tech_msg,
                        "Wisconsin",
                        hint,
                    )
                )

        agency_state = _find_text(root, "dAgency.04")
        if agency_state is not None and agency_state.upper() != "WI":
            issues.append(
                _make_issue(
                    severity="warning",
                    stage="wi_schematron",
                    rule_id="WI-006",
                    element_id="dAgency.04",
                    plain_message=f"Agency State (dAgency.04) is '{agency_state}', expected 'WI' for Wisconsin submissions.",
                    technical_message=f"dAgency.04 value={agency_state!r}; expected 'WI'.",
                    rule_source="Wisconsin",
                    fix_hint="Set dAgency.04 to 'WI' for Wisconsin EMS agency submissions.",
                )
            )

        return issues

    def _stage_wi_state(self, root: ET.Element) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        gender_val = _find_text(root, "ePatient.13")
        if gender_val is not None and gender_val not in VALID_GENDER_CODES:
            issues.append(
                _make_issue(
                    severity="error",
                    stage="wi_state",
                    rule_id="WI-STATE-001",
                    element_id="ePatient.13",
                    plain_message=f"Patient Gender code '{gender_val}' is not a valid NEMSIS code.",
                    technical_message=f"ePatient.13 value={gender_val!r}; valid codes: {sorted(VALID_GENDER_CODES)}",
                    rule_source="Wisconsin",
                    fix_hint="Use a valid NEMSIS gender code: 9906001 (Male), 9906003 (Female), 9906009 (Unknown).",
                )
            )

        acuity_val = _find_text(root, "eDisposition.27")
        if acuity_val is not None and acuity_val not in VALID_ACUITY_CODES:
            issues.append(
                _make_issue(
                    severity="error",
                    stage="wi_state",
                    rule_id="WI-STATE-002",
                    element_id="eDisposition.27",
                    plain_message=f"Final Patient Acuity code '{acuity_val}' is not a valid NEMSIS code.",
                    technical_message=f"eDisposition.27 value={acuity_val!r}; valid codes: {sorted(VALID_ACUITY_CODES)}",
                    rule_source="Wisconsin",
                    fix_hint="Use a valid NEMSIS final acuity code from the eDisposition.27 value set.",
                )
            )

        timestamp_fields = ["eTimes.01", "eTimes.03", "eTimes.06", "eTimes.07", "eTimes.11"]
        for ts_field in timestamp_fields:
            val = _find_text(root, ts_field)
            if val is not None and not _ISO8601_RE.match(val):
                section, label = _ui_info(ts_field)
                issues.append(
                    _make_issue(
                        severity="error",
                        stage="wi_state",
                        rule_id="WI-STATE-003",
                        element_id=ts_field,
                        plain_message=f"{label} has an invalid date/time format: '{val}'.",
                        technical_message=f"{ts_field} value={val!r} does not match ISO 8601 pattern.",
                        rule_source="Wisconsin",
                        fix_hint="Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ or with offset (e.g. 2024-01-15T14:30:00-06:00).",
                    )
                )

        return issues
