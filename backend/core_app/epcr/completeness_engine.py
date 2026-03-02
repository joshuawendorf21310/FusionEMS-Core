from __future__ import annotations

from typing import Any

ELEMENT_FIELD_MAP: dict[str, dict[str, str]] = {
    "eRecord.01": {
        "path": "chart_id",
        "label": "PCR Number",
        "section": "Record",
        "severity": "error",
    },
    "eIncident.01": {
        "path": "dispatch.incident_number",
        "label": "Incident Number",
        "section": "Incident",
        "severity": "error",
    },
    "eTimes.01": {
        "path": "dispatch.psap_call_time",
        "label": "PSAP Call Time",
        "section": "Times",
        "severity": "error",
    },
    "eTimes.06": {
        "path": "dispatch.arrived_scene_time",
        "label": "Arrived Scene Time",
        "section": "Times",
        "severity": "error",
    },
    "eTimes.07": {
        "path": "dispatch.patient_contact_time",
        "label": "Patient Contact Time",
        "section": "Times",
        "severity": "error",
    },
    "ePatient.02": {
        "path": "patient.dob",
        "label": "Patient DOB",
        "section": "Patient",
        "severity": "error",
    },
    "ePatient.03": {
        "path": "patient.last_name",
        "label": "Patient Last Name",
        "section": "Patient",
        "severity": "error",
    },
    "ePatient.04": {
        "path": "patient.first_name",
        "label": "Patient First Name",
        "section": "Patient",
        "severity": "error",
    },
    "ePatient.13": {
        "path": "patient.gender",
        "label": "Patient Gender",
        "section": "Patient",
        "severity": "error",
    },
    "eResponse.13": {
        "path": "dispatch.responding_unit",
        "label": "Unit Call Sign",
        "section": "Response",
        "severity": "error",
    },
    "eSituation.11": {
        "path": "assessments[0].chief_complaint",
        "label": "Primary Impression",
        "section": "Situation",
        "severity": "error",
    },
    "eNarrative.01": {
        "path": "narrative",
        "label": "Narrative",
        "section": "Narrative",
        "severity": "warning",
    },
    "eDisposition.27": {
        "path": "disposition.patient_disposition_code",
        "label": "Patient Disposition",
        "section": "Disposition",
        "severity": "error",
    },
}

MODE_EXTRA: dict[str, list[str]] = {
    "acls": ["acls.initial_rhythm", "acls.code_start_time"],
    "cct": ["cct.transfer_source_facility"],
    "hems": ["hems.wheels_up_time", "hems.wheels_down_time", "hems.mission_number"],
    "fire": [],
}


class CompletenessEngine:
    def score_chart(self, chart: dict[str, Any], mode: str = "bls") -> dict[str, Any]:
        missing = []
        present = []

        for elem_id, meta in ELEMENT_FIELD_MAP.items():
            val = self._get_nested(chart, meta["path"])
            if val and str(val).strip():
                present.append(elem_id)
            else:
                missing.append(
                    {
                        "element_id": elem_id,
                        "field_path": meta["path"],
                        "label": meta["label"],
                        "section": meta["section"],
                        "severity": meta["severity"],
                    }
                )

        vitals = chart.get("vitals", [])
        if not vitals:
            missing.append(
                {
                    "element_id": "eVitals",
                    "field_path": "vitals",
                    "label": "At least one Vital Set",
                    "section": "Vitals",
                    "severity": "error",
                }
            )
        else:
            present.append("eVitals")

        for extra_path in MODE_EXTRA.get(mode, []):
            val = self._get_nested(chart, extra_path)
            if not val or not str(val).strip():
                missing.append(
                    {
                        "element_id": extra_path,
                        "field_path": extra_path,
                        "label": extra_path,
                        "section": mode.upper(),
                        "severity": "warning",
                    }
                )

        total = len(ELEMENT_FIELD_MAP) + 1 + len(MODE_EXTRA.get(mode, []))
        errors_only = [m for m in missing if m["severity"] == "error"]
        pct = round((len(present) / total) * 100, 1) if total else 100.0
        return {
            "score": pct,
            "pct": pct,
            "missing": missing,
            "present": present,
            "error_count": len(errors_only),
            "warning_count": len(missing) - len(errors_only),
        }

    def score_for_submission(self, chart: dict[str, Any], state_code: str = "WI") -> dict[str, Any]:
        result = self.score_chart(chart, mode=chart.get("chart_mode", "bls"))
        blocking = [m["label"] for m in result["missing"] if m["severity"] == "error"]
        return {
            "ready": len(blocking) == 0,
            "blocking_issues": blocking,
            "score": result["score"],
            "pct": result["pct"],
        }

    def _get_nested(self, chart: dict[str, Any], path: str) -> Any:
        import re

        current: Any = chart
        parts = re.split(r"\.", path)
        for part in parts:
            if current is None:
                return None
            m = re.match(r"^(\w+)\[(\d+)\]$", part)
            if m:
                key, idx = m.group(1), int(m.group(2))
                lst = current.get(key, []) if isinstance(current, dict) else None
                if not isinstance(lst, list) or idx >= len(lst):
                    return None
                current = lst[idx]
            else:
                current = current.get(part) if isinstance(current, dict) else None
        return current
