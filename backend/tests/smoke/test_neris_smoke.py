from __future__ import annotations

import os
import uuid
import pytest
from unittest.mock import patch


SKIP_IF_NO_DB = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping smoke tests"
)


@SKIP_IF_NO_DB
class TestNERISSmoke:

    @pytest.fixture(autouse=True)
    def setup(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(os.environ["DATABASE_URL"])
        Session = sessionmaker(bind=engine)
        self.db = Session()
        self.tenant_id = uuid.uuid4()
        self.actor_id = uuid.uuid4()
        from core_app.services.event_publisher import get_event_publisher
        self.publisher = get_event_publisher()
        yield
        self.db.close()

    @pytest.mark.asyncio
    async def test_01_pack_compiler_default_value_sets(self):
        """Pack compiler produces valid default value sets when no files present."""
        from core_app.neris.pack_compiler import _wi_default_value_sets
        vs = _wi_default_value_sets()
        assert "INCIDENT_TYPE" in vs
        assert "UNIT_TYPE" in vs
        assert len(vs["INCIDENT_TYPE"]["items"]) > 5
        assert any(i["code"] == "100" for i in vs["INCIDENT_TYPE"]["items"])

    @pytest.mark.asyncio
    async def test_02_pack_compiler_default_incident_sections(self):
        """Pack compiler produces required incident sections by default."""
        from core_app.neris.pack_compiler import _wi_default_incident_sections
        sections = _wi_default_incident_sections()
        assert len(sections) >= 4
        section_ids = [s["id"] for s in sections]
        assert "incident.basics" in section_ids
        assert "incident.units" in section_ids
        assert "incident.actions" in section_ids
        basics = next(s for s in sections if s["id"] == "incident.basics")
        field_paths = [f["path"] for f in basics["fields"]]
        assert "incident.incident_number" in field_paths
        assert "incident.start_datetime" in field_paths
        assert "incident.type_code" in field_paths

    @pytest.mark.asyncio
    async def test_03_validator_missing_required_fields(self):
        """Validator returns errors for missing required fields."""
        from core_app.neris.validator import NERISValidator
        from core_app.neris.pack_compiler import _wi_default_incident_sections, _wi_default_value_sets

        # Build a minimal rules dict inline (no DB needed)
        vs = _wi_default_value_sets()
        rules = {
            "entity_type": "INCIDENT",
            "sections": _wi_default_incident_sections(),
            "value_sets": {k: {"allowed": [i["code"] for i in v.get("items", [])]} for k, v in vs.items()},
            "constraints": [],
        }

        # Patch _get_rules to return our inline rules
        validator = NERISValidator(self.db, self.publisher, self.tenant_id)
        pack_id = uuid.uuid4()
        
        with patch.object(validator, "_get_rules", return_value=rules):
            issues = validator.validate(pack_id, "INCIDENT", {})

        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 3
        paths = [i["path"] for i in errors]
        assert "incident.incident_number" in paths
        assert "incident.start_datetime" in paths
        assert "incident.type_code" in paths

    @pytest.mark.asyncio
    async def test_04_validator_valid_incident_passes(self):
        """Validator returns no errors for a valid incident payload."""
        from core_app.neris.validator import NERISValidator
        from core_app.neris.pack_compiler import _wi_default_incident_sections, _wi_default_value_sets

        vs = _wi_default_value_sets()
        rules = {
            "entity_type": "INCIDENT",
            "sections": _wi_default_incident_sections(),
            "value_sets": {k: {"allowed": [i["code"] for i in v.get("items", [])]} for k, v in vs.items()},
            "constraints": [
                {"id": "incident.end_after_start", "type": "compare", "a": "incident.end_datetime", "op": ">=", "b": "incident.start_datetime", "severity": "warning", "message": "End time should be after start."},
            ],
        }

        payload = {
            "incident": {
                "incident_number": "WI-2026-001",
                "start_datetime": "2026-02-27T10:00:00+00:00",
                "end_datetime": "2026-02-27T11:30:00+00:00",
                "type_code": "100",
                "location": {
                    "address": "123 Main St",
                    "city": "Madison",
                    "state": "WI",
                    "zip": "53703",
                },
            }
        }

        validator = NERISValidator(self.db, self.publisher, self.tenant_id)
        pack_id = uuid.uuid4()
        with patch.object(validator, "_get_rules", return_value=rules):
            issues = validator.validate(pack_id, "INCIDENT", payload)

        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_05_validator_invalid_value_set(self):
        """Validator catches invalid value set codes."""
        from core_app.neris.validator import NERISValidator
        from core_app.neris.pack_compiler import _wi_default_incident_sections, _wi_default_value_sets

        vs = _wi_default_value_sets()
        rules = {
            "entity_type": "INCIDENT",
            "sections": _wi_default_incident_sections(),
            "value_sets": {k: {"allowed": [i["code"] for i in v.get("items", [])]} for k, v in vs.items()},
            "constraints": [],
        }
        payload = {
            "incident": {
                "incident_number": "WI-2026-002",
                "start_datetime": "2026-02-27T10:00:00+00:00",
                "type_code": "INVALID_CODE_XYZ",
                "location": {"address": "123 Main St", "city": "Madison", "state": "WI"},
            }
        }
        validator = NERISValidator(self.db, self.publisher, self.tenant_id)
        pack_id = uuid.uuid4()
        with patch.object(validator, "_get_rules", return_value=rules):
            issues = validator.validate(pack_id, "INCIDENT", payload)
        vs_errors = [i for i in issues if "invalid_value" in i["rule_id"]]
        assert len(vs_errors) >= 1
        assert any("INVALID_CODE_XYZ" in i["message"] for i in vs_errors)

    @pytest.mark.asyncio
    async def test_06_copilot_fallback_on_no_openai(self):
        """Copilot returns structured fallback when OpenAI is unavailable."""
        from core_app.neris.copilot import NERISCopilot
        issues = [
            {"severity": "error", "path": "incident.type_code", "ui_section": "Incident Basics",
             "message": "Incident Type is required.", "suggested_fix": "Select a type from the allowed list.", "rule_id": "incident.type_code.required", "entity_type": "INCIDENT", "field_label": "Incident Type"}
        ]
        with patch("core_app.neris.copilot.AiService") as MockAI:
            MockAI.return_value.chat.side_effect = Exception("openai unavailable")
            copilot = NERISCopilot()
            result = copilot.explain_issues(issues, {"state": "WI"})
        assert "summary" in result
        assert "actions" in result
        assert len(result["actions"]) >= 1
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_07_copilot_empty_issues(self):
        """Copilot returns ready message for empty issues."""
        from core_app.neris.copilot import NERISCopilot
        copilot = NERISCopilot.__new__(NERISCopilot)  # avoid calling __init__ (needs OpenAI key)
        result = copilot.explain_issues([])
        assert result["confidence"] == 1.0
        assert result["actions"] == []

    @pytest.mark.asyncio
    async def test_08_exporter_build_entity_payload_structure(self):
        """Exporter builds valid entity payload structure from dept + stations + apparatus."""
        from core_app.neris.exporter import NERISExporter
        exporter = NERISExporter(self.db, self.publisher, self.tenant_id, self.actor_id)

        dept_id = uuid.uuid4()
        mock_dept = {"id": str(dept_id), "version": 1, "data": {"name": "Madison FD", "state": "WI", "primary_contact_name": "Chief Smith", "primary_contact_email": "chief@madison.wi.gov", "primary_contact_phone": "608-555-0100"}}
        mock_stations = [{"id": str(uuid.uuid4()), "data": {"department_id": str(dept_id), "name": "Station 1", "address_json": {"street": "100 Main St", "city": "Madison"}}}]
        mock_apparatus = [{"id": str(uuid.uuid4()), "data": {"department_id": str(dept_id), "unit_id": "Engine 1", "unit_type_code": "ENGINE"}}]

        with patch.object(exporter.svc.repo("fire_departments"), "get", return_value=mock_dept), \
             patch.object(exporter.svc.repo("fire_stations"), "list", return_value=mock_stations), \
             patch.object(exporter.svc.repo("fire_apparatus"), "list", return_value=mock_apparatus):
            payload = exporter.build_entity_payload(dept_id)

        assert "department" in payload
        assert payload["department"]["name"] == "Madison FD"
        assert payload["department"]["reporting_mode"] == "RMS"
        assert len(payload["department"]["stations"]) == 1
        assert payload["department"]["stations"][0]["name"] == "Station 1"
        assert len(payload["department"]["apparatus"]) == 1
        assert payload["department"]["apparatus"][0]["unit_id"] == "Engine 1"

    @pytest.mark.asyncio
    async def test_09_onboarding_wizard_steps_structure(self):
        """Onboarding wizard has correct step definitions."""
        from core_app.neris.onboarding_wizard import ONBOARDING_STEPS, WI_DSPS_GOLIVE_CHECKLIST
        assert len(ONBOARDING_STEPS) == 8
        step_ids = [s["id"] for s in ONBOARDING_STEPS]
        assert "department_identity" in step_ids
        assert "reporting_mode" in step_ids
        assert "sample_incident" in step_ids
        assert "golive_checklist" in step_ids
        assert len(WI_DSPS_GOLIVE_CHECKLIST) >= 5

    @pytest.mark.asyncio
    async def test_10_pack_compiler_yaml_parsing(self):
        """Pack compiler parses YAML value sets correctly."""
        from core_app.neris.pack_compiler import NERISPackCompiler
        compiler = NERISPackCompiler(self.db, self.publisher, self.tenant_id, self.actor_id)
        test_yaml = b"""
code: TEST_SET
name: Test Value Set
values:
  - code: A
    display: Alpha
  - code: B
    display: Beta
  - code: C
    display: Gamma
"""
        raw_files = {"valuesets/test_set.yaml": test_yaml}
        vs = compiler._parse_value_sets(raw_files)
        assert "TEST_SET" in vs
        assert len(vs["TEST_SET"]["items"]) == 3
        codes = [i["code"] for i in vs["TEST_SET"]["items"]]
        assert "A" in codes and "B" in codes and "C" in codes

    @pytest.mark.asyncio
    async def test_11_pack_compiler_csv_parsing(self):
        """Pack compiler parses CSV value sets correctly."""
        from core_app.neris.pack_compiler import NERISPackCompiler
        compiler = NERISPackCompiler(self.db, self.publisher, self.tenant_id, self.actor_id)
        test_csv = b"code,description\n100,Fire\n200,EMS\n300,Rescue\n"
        raw_files = {"valuesets/incident_types.csv": test_csv}
        vs = compiler._parse_value_sets(raw_files)
        assert "INCIDENT_TYPES" in vs
        assert len(vs["INCIDENT_TYPES"]["items"]) == 3

    @pytest.mark.asyncio
    async def test_12_validator_path_resolver(self):
        """Validator path resolver handles nested dot paths."""
        from core_app.neris.validator import _get_path
        payload = {"incident": {"location": {"city": "Madison", "state": "WI"}, "type_code": "100"}}
        assert _get_path(payload, "incident.type_code") == "100"
        assert _get_path(payload, "incident.location.city") == "Madison"
        assert _get_path(payload, "incident.missing_field") is None
        assert _get_path(payload, "nonexistent.path") is None
