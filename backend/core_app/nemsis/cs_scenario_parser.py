from __future__ import annotations

import io
import json
import uuid
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from typing import Any


@dataclass
class ScenarioSection:
    name: str
    element_count: int


@dataclass
class CandSScenario:
    scenario_id: str
    name: str
    summary: str
    dataset_type: str
    expected_result: str
    sections_involved: list[ScenarioSection]
    raw_data: dict[str, Any]
    nemsis_version: str
    state_code: str
    test_type: str


_SECTION_KEYS = {
    "patient": ["ePatient", "patient", "Patient"],
    "vitals": ["eVitals", "vitals", "Vitals"],
    "meds": ["eMedications", "medications", "Medications", "meds"],
    "procedures": ["eProcedures", "procedures", "Procedures"],
    "times": ["eTimes", "times", "Times"],
    "disposition": ["eDisposition", "disposition", "Disposition"],
}


def _detect_sections_from_dict(data: dict[str, Any]) -> list[ScenarioSection]:
    sections = []
    raw_str = json.dumps(data)
    for section_name, keys in _SECTION_KEYS.items():
        count = sum(raw_str.count(k) for k in keys)
        if count > 0:
            sections.append(ScenarioSection(name=section_name, element_count=count))
    return sections


def _detect_sections_from_xml_str(xml_str: str) -> list[ScenarioSection]:
    sections = []
    for section_name, keys in _SECTION_KEYS.items():
        count = sum(xml_str.count(k) for k in keys)
        if count > 0:
            sections.append(ScenarioSection(name=section_name, element_count=count))
    return sections


def _normalize_expected_result(val: str | None) -> str:
    if val is None:
        return "PASS"
    v = val.upper().strip()
    if "FAIL" in v:
        return "FAIL"
    return "PASS"


def _detect_test_type(data: dict[str, Any]) -> str:
    raw = json.dumps(data).lower()
    if "schematron" in raw:
        return "schematron"
    if "validation" in raw:
        return "validation"
    return "conformance"


class CandSParser:
    def parse_json_scenario(self, content: bytes) -> CandSScenario | None:
        try:
            data: dict[str, Any] = json.loads(content.decode("utf-8", errors="replace"))
        except Exception:
            return None

        scenario_id = (
            data.get("scenarioId")
            or data.get("scenario_id")
            or data.get("id")
            or str(uuid.uuid4())
        )
        name = (
            data.get("name")
            or data.get("scenarioName")
            or data.get("scenario_name")
            or scenario_id
        )
        summary = data.get("description") or data.get("summary") or ""
        dataset_type = (
            data.get("dataSetType")
            or data.get("dataset_type")
            or data.get("DataSetType")
            or "EMS"
        )
        expected_result = _normalize_expected_result(
            data.get("expectedResult") or data.get("expected_result") or data.get("ExpectedResult")
        )
        nemsis_version = (
            data.get("nemsis:version")
            or data.get("nemsisVersion")
            or data.get("nemsis_version")
            or "3.5.1"
        )
        state_code = (
            data.get("stateCode")
            or data.get("state_code")
            or data.get("state")
            or "NATIONAL"
        )
        test_type = _detect_test_type(data)
        sections = _detect_sections_from_dict(data)

        return CandSScenario(
            scenario_id=str(scenario_id),
            name=str(name),
            summary=str(summary),
            dataset_type=str(dataset_type).upper(),
            expected_result=expected_result,
            sections_involved=sections,
            raw_data=data,
            nemsis_version=str(nemsis_version),
            state_code=str(state_code).upper(),
            test_type=test_type,
        )

    def parse_xml_scenario(self, content: bytes) -> CandSScenario | None:
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return None

        def _find(tag: str) -> str | None:
            for el in root.iter():
                local = el.tag.split("}", 1)[-1] if "}" in el.tag else el.tag
                if local == tag:
                    return (el.text or "").strip() or None
            return None

        scenario_id = _find("ScenarioId") or _find("scenarioId") or str(uuid.uuid4())
        name = _find("ScenarioName") or _find("scenarioName") or _find("Name") or scenario_id
        summary = _find("Description") or _find("Summary") or ""
        dataset_type = (_find("DataSetType") or _find("dataSetType") or "EMS").upper()
        expected_result = _normalize_expected_result(_find("ExpectedResult") or _find("expectedResult"))
        nemsis_version = _find("NEMSISVersion") or _find("nemsisVersion") or "3.5.1"
        state_code = (_find("StateCode") or _find("stateCode") or "NATIONAL").upper()
        xml_str = content.decode(errors="ignore")
        test_type = "schematron" if "schematron" in xml_str.lower() else "conformance"
        sections = _detect_sections_from_xml_str(xml_str)

        raw_data: dict[str, Any] = {
            "scenario_id": scenario_id,
            "name": name,
            "description": summary,
            "dataset_type": dataset_type,
            "expected_result": expected_result,
            "nemsis_version": nemsis_version,
            "state_code": state_code,
        }

        return CandSScenario(
            scenario_id=str(scenario_id),
            name=str(name),
            summary=str(summary),
            dataset_type=dataset_type,
            expected_result=expected_result,
            sections_involved=sections,
            raw_data=raw_data,
            nemsis_version=str(nemsis_version),
            state_code=state_code,
            test_type=test_type,
        )

    def detect_and_parse(self, filename: str, content: bytes) -> CandSScenario | None:
        lower = filename.lower()
        if lower.endswith(".json"):
            return self.parse_json_scenario(content)
        if lower.endswith(".xml"):
            return self.parse_xml_scenario(content)
        preview = content[:200].decode(errors="ignore")
        if preview.lstrip().startswith("{"):
            return self.parse_json_scenario(content)
        if preview.lstrip().startswith("<"):
            return self.parse_xml_scenario(content)
        return None

    def parse_zip_bundle(self, zip_content: bytes) -> list[CandSScenario]:
        scenarios: list[CandSScenario] = []
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_content))
        except Exception:
            return scenarios

        with zf:
            for name in zf.namelist():
                lower = name.lower()
                if not (lower.endswith(".json") or lower.endswith(".xml")):
                    continue
                try:
                    file_content = zf.read(name)
                except Exception:
                    continue
                scenario = self.detect_and_parse(name, file_content)
                if scenario is not None:
                    scenarios.append(scenario)

        return scenarios
