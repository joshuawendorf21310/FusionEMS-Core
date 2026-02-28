from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from core_app.ai.service import AiService


class SmartTextEngine:
    def __init__(self) -> None:
        self._ai = AiService()

    def generate_narrative(self, chart: dict[str, Any], tone: str = "clinical") -> dict[str, Any]:
        summary = self._build_chart_summary(chart)
        cache_key = self._cache_key(chart, f"narrative_{tone}")
        system = (
            "You are an expert EMS documentation specialist. Generate a professional ePCR narrative. "
            "Use ONLY the provided data. Do not invent, assume, or add clinical details not explicitly stated. "
            "Output only the narrative text, no headings."
        )
        user = f"Tone: {tone}\n\nCall data:\n{summary}\n\nGenerate narrative:"
        text, meta = self._ai.chat(system=system, user=user)
        return {
            "narrative": text,
            "tone": tone,
            "cache_key": cache_key,
            "token_usage": meta.get("usage", {}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_handoff_summary(self, chart: dict[str, Any]) -> dict[str, Any]:
        summary = self._build_chart_summary(chart)
        cache_key = self._cache_key(chart, "handoff")
        system = (
            "You are an EMS provider generating a verbal handoff summary in SBAR format. "
            "Use ONLY the provided chart data."
        )
        user = f"Generate a concise SBAR handoff:\n{summary}"
        text, meta = self._ai.chat(system=system, user=user)
        return {
            "summary": text,
            "format": "SBAR",
            "cache_key": cache_key,
            "token_usage": meta.get("usage", {}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_billing_synopsis(self, chart: dict[str, Any]) -> dict[str, Any]:
        summary = self._build_chart_summary(chart)
        cache_key = self._cache_key(chart, "billing_synopsis")
        system = (
            "You are an EMS billing specialist. Generate a billing-ready synopsis from this chart. "
            "Use ONLY the provided data."
        )
        user = f"Generate billing synopsis:\n{summary}"
        text, meta = self._ai.chat(system=system, user=user)
        return {
            "synopsis": text,
            "cache_key": cache_key,
            "token_usage": meta.get("usage", {}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def detect_missing_documentation(self, chart: dict[str, Any], mode: str = "bls") -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        procedures = chart.get("procedures") or []
        vitals = chart.get("vitals") or []
        medications = chart.get("medications") or []
        assessments = chart.get("assessments") or []
        disposition = chart.get("disposition") or {}
        consent = chart.get("consent") or {}
        patient = chart.get("patient") or {}
        narrative = chart.get("narrative") or ""

        proc_names_lower = [(p.get("procedure_name") or "").lower() for p in procedures]

        intubated = any("intubat" in n for n in proc_names_lower)
        has_etco2 = any(v.get("etco2") is not None for v in vitals)
        if intubated and not has_etco2:
            issues.append({
                "issue": "Intubation documented but no ETCO2 value recorded",
                "severity": "error",
                "suggestion": "Add an EtCO2 reading to confirm tube placement.",
            })

        if mode == "acls":
            has_rhythm = any(v.get("rhythm") for v in vitals)
            if not has_rhythm:
                issues.append({
                    "issue": "ACLS mode: no rhythm documented",
                    "severity": "error",
                    "suggestion": "Document cardiac rhythm in at least one vital set.",
                })

        disposition_code = (disposition.get("patient_disposition_code") or "").lower()
        disposition_transport = (disposition.get("transport_disposition") or "").lower()
        is_refusal = "refusal" in disposition_code or "refused" in disposition_code or "refusal" in disposition_transport or "refused" in disposition_transport
        consent_type = (consent.get("consent_type") or "").strip()
        consented_by = (consent.get("consented_by") or "").strip()
        if is_refusal and not consent_type and not consented_by:
            issues.append({
                "issue": "Refusal documented but consent/capacity block incomplete",
                "severity": "error",
                "suggestion": "Complete the consent block with refusal reason and capacity confirmation.",
            })

        first_assessment = assessments[0] if assessments else {}
        allergies = first_assessment.get("allergies") or []
        if medications and not allergies:
            issues.append({
                "issue": "Medications given but allergy documentation missing",
                "severity": "warning",
                "suggestion": "Document patient allergies or NKDA in the first assessment block.",
            })

        if mode == "cct":
            cct_block = chart.get("cct")
            if not cct_block:
                issues.append({
                    "issue": "CCT mode: CCT documentation block missing",
                    "severity": "error",
                    "suggestion": "Complete the CCT block with drip infusions and vent settings.",
                })

        if mode == "hems":
            hems_block = chart.get("hems")
            if not hems_block:
                issues.append({
                    "issue": "HEMS mode: HEMS documentation block missing",
                    "severity": "error",
                    "suggestion": "Complete the HEMS block with wheels-up/down times and mission number.",
                })

        defib_done = any("defibr" in n or "shock" in n for n in proc_names_lower)
        acls_block = chart.get("acls")
        if defib_done and not acls_block:
            issues.append({
                "issue": "Defibrillation documented but ACLS block missing",
                "severity": "warning",
                "suggestion": "Complete the ACLS block with defibrillation events and code times.",
            })

        if not narrative or len(narrative.strip()) < 50:
            issues.append({
                "issue": "Narrative is missing or too brief",
                "severity": "warning",
                "suggestion": "Write a narrative of at least 50 characters covering response, assessment, treatment, and transport.",
            })

        if not vitals:
            issues.append({
                "issue": "No vital signs documented",
                "severity": "error",
                "suggestion": "Record at least one set of vital signs.",
            })

        first_name = (patient.get("first_name") or "").strip()
        last_name = (patient.get("last_name") or "").strip()
        if not first_name or not last_name:
            issues.append({
                "issue": "Patient name missing",
                "severity": "error",
                "suggestion": "Enter the patient's first and last name.",
            })

        blocking = any(i["severity"] == "error" for i in issues)
        return {"issues": issues, "count": len(issues), "has_blocking": blocking}

    def detect_contradictions(self, chart: dict[str, Any]) -> dict[str, Any]:
        contradictions: list[dict[str, Any]] = []

        assessments = chart.get("assessments") or []
        first_assessment = assessments[0] if assessments else {}
        allergies = first_assessment.get("allergies") or []
        history = str(first_assessment.get("history") or "")
        if "NKDA" in history.upper() and len(allergies) > 0:
            contradictions.append({
                "field_a": "assessments[0].history",
                "field_b": "assessments[0].allergies",
                "description": "NKDA documented in history but allergy list is not empty",
            })

        patient = chart.get("patient") or {}
        dob_str = patient.get("dob") or ""
        if dob_str:
            try:
                from datetime import date
                dob = date.fromisoformat(dob_str)
                age_years = (date.today() - dob).days // 365
                if age_years < 12:
                    for med in (chart.get("medications") or []):
                        try:
                            dose = float(med.get("dose") or 0)
                            unit = (med.get("dose_unit") or "").lower()
                            if "mg" in unit and dose > 500:
                                contradictions.append({
                                    "field_a": "patient.dob",
                                    "field_b": f"medications[{med.get('medication_name', '')}].dose",
                                    "description": (
                                        f"Pediatric patient (age ~{age_years}) has adult-level dose "
                                        f"({dose} {unit}) of {med.get('medication_name', 'unknown')}"
                                    ),
                                })
                        except (TypeError, ValueError):
                            pass
            except (ValueError, TypeError):
                pass

        death_codes = {"4217007", "4217009", "dead", "deceased", "pronounced"}
        disposition = chart.get("disposition") or {}
        disposition_code = str(disposition.get("patient_disposition_code") or "").lower()
        patient_deceased = disposition_code in death_codes or any(d in disposition_code for d in ("dead", "deceased"))

        dispatch = chart.get("dispatch") or {}
        contact_time_str = dispatch.get("patient_contact_time") or ""
        vitals = chart.get("vitals") or []
        if patient_deceased and vitals and contact_time_str:
            try:
                contact_ts = datetime.fromisoformat(contact_time_str.replace("Z", "+00:00"))
                for vital in vitals:
                    recorded_str = vital.get("recorded_at") or ""
                    if not recorded_str:
                        continue
                    recorded_ts = datetime.fromisoformat(recorded_str.replace("Z", "+00:00"))
                    hr = vital.get("heart_rate")
                    if recorded_ts > contact_ts and hr and int(hr) != 0:
                        contradictions.append({
                            "field_a": "disposition.patient_disposition_code",
                            "field_b": f"vitals[recorded_at={recorded_str}].heart_rate",
                            "description": "Vital signs with non-zero heart rate recorded after patient declared deceased",
                        })
                        break
            except (TypeError, ValueError):
                pass

        for i, vital in enumerate(vitals):
            spo2 = vital.get("spo2")
            if spo2 is not None:
                try:
                    if float(spo2) > 100:
                        contradictions.append({
                            "field_a": f"vitals[{i}].spo2",
                            "field_b": "physiological_max",
                            "description": f"Impossible SpO2 value: {spo2}% (max is 100%)",
                        })
                except (TypeError, ValueError):
                    pass

            hr = vital.get("heart_rate")
            if hr is not None:
                try:
                    if int(hr) > 300:
                        contradictions.append({
                            "field_a": f"vitals[{i}].heart_rate",
                            "field_b": "physiological_max",
                            "description": f"Implausible heart rate: {hr} bpm (exceeds 300)",
                        })
                except (TypeError, ValueError):
                    pass

            gcs_total = vital.get("gcs_total")
            gcs_eye = vital.get("gcs_eye")
            gcs_verbal = vital.get("gcs_verbal")
            gcs_motor = vital.get("gcs_motor")
            if gcs_total is not None and gcs_eye is not None and gcs_verbal is not None and gcs_motor is not None:
                try:
                    if int(gcs_eye) + int(gcs_verbal) + int(gcs_motor) != int(gcs_total):
                        contradictions.append({
                            "field_a": f"vitals[{i}].gcs_total",
                            "field_b": f"vitals[{i}].gcs_eye+gcs_verbal+gcs_motor",
                            "description": (
                                f"GCS component mismatch: eye({gcs_eye}) + verbal({gcs_verbal}) + "
                                f"motor({gcs_motor}) = {int(gcs_eye)+int(gcs_verbal)+int(gcs_motor)}, "
                                f"but gcs_total={gcs_total}"
                            ),
                        })
                except (TypeError, ValueError):
                    pass

        return {"contradictions": contradictions, "count": len(contradictions)}

    def _build_chart_summary(self, chart: dict[str, Any]) -> str:
        parts: list[str] = []

        assessments = chart.get("assessments") or []
        primary = assessments[0] if assessments else {}
        chief_complaint = primary.get("chief_complaint") or chart.get("dispatch", {}).get("complaint_reported") or "Unknown"
        parts.append(f"Chief complaint: {chief_complaint}")
        parts.append(f"Mode: {chart.get('chart_mode', 'bls')}")

        vitals = chart.get("vitals") or []
        if vitals:
            v = vitals[0]
            parts.append(
                f"Vitals (first): HR={v.get('heart_rate', 'N/A')} "
                f"BP={v.get('systolic_bp', 'N/A')}/{v.get('diastolic_bp', 'N/A')} "
                f"SpO2={v.get('spo2', 'N/A')}% RR={v.get('respiratory_rate', 'N/A')}"
            )
            if len(vitals) > 1:
                v2 = vitals[-1]
                parts.append(
                    f"Vitals (last): HR={v2.get('heart_rate', 'N/A')} "
                    f"BP={v2.get('systolic_bp', 'N/A')}/{v2.get('diastolic_bp', 'N/A')} "
                    f"SpO2={v2.get('spo2', 'N/A')}% RR={v2.get('respiratory_rate', 'N/A')}"
                )

        medications = chart.get("medications") or []
        med_names = [m.get("medication_name") or "unknown" for m in medications]
        parts.append(f"Medications: {', '.join(med_names) if med_names else 'None'}")

        procedures = chart.get("procedures") or []
        proc_names = [p.get("procedure_name") or "unknown" for p in procedures]
        parts.append(f"Procedures: {', '.join(proc_names) if proc_names else 'None'}")

        narrative = chart.get("narrative") or ""
        if narrative:
            parts.append(f"Narrative snippet: {narrative[:200]}")

        disposition = chart.get("disposition") or {}
        parts.append(
            f"Disposition: {disposition.get('patient_disposition_code', 'N/A')} "
            f"to {disposition.get('destination_name', 'N/A')}"
        )

        return "\n".join(parts)

    def _cache_key(self, chart: dict[str, Any], prompt_type: str) -> str:
        exclude = {"updated_at", "sync_status", "completeness_score", "completeness_issues"}
        filtered = {k: v for k, v in chart.items() if k not in exclude}
        serialized = json.dumps(filtered, sort_keys=True, default=str)
        return hashlib.sha256(f"{serialized}:{prompt_type}".encode("utf-8")).hexdigest()
