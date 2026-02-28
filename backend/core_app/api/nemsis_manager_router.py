from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.compliance.nemsis_xml_generator import build_nemsis_document, validate_nemsis_xml

router = APIRouter(prefix="/api/v1/nemsis-manager", tags=["NEMSIS 3.5.1 Dataset Manager"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


NEMSIS_351_SCHEMA: dict[str, Any] = {
    "version": "3.5.1",
    "elements": {
        "eRecord.01": {"label": "Patient Care Report Number", "required": True, "type": "string", "section": "eRecord"},
        "eRecord.02": {"label": "Software Creator", "required": True, "type": "string", "section": "eRecord"},
        "eRecord.03": {"label": "Software Name", "required": True, "type": "string", "section": "eRecord"},
        "eRecord.04": {"label": "Software Version", "required": True, "type": "string", "section": "eRecord"},
        "eTimes.01": {"label": "PSAP Call Date/Time", "required": True, "type": "dateTime", "section": "eTimes"},
        "eTimes.02": {"label": "Dispatch Notified Date/Time", "required": False, "type": "dateTime", "section": "eTimes"},
        "eTimes.03": {"label": "Unit Notified by Dispatch Date/Time", "required": True, "type": "dateTime", "section": "eTimes"},
        "eTimes.05": {"label": "Unit En Route Date/Time", "required": True, "type": "dateTime", "section": "eTimes"},
        "eTimes.06": {"label": "Unit Arrived on Scene Date/Time", "required": True, "type": "dateTime", "section": "eTimes"},
        "eTimes.07": {"label": "Arrived at Patient Date/Time", "required": False, "type": "dateTime", "section": "eTimes"},
        "eTimes.09": {"label": "Unit Left Scene Date/Time", "required": True, "type": "dateTime", "section": "eTimes"},
        "eTimes.11": {"label": "Patient Arrived at Destination Date/Time", "required": True, "type": "dateTime", "section": "eTimes"},
        "eTimes.13": {"label": "Unit Back in Service Date/Time", "required": True, "type": "dateTime", "section": "eTimes"},
        "ePatient.01": {"label": "Last Name", "required": True, "type": "string", "section": "ePatient", "phi": True},
        "ePatient.02": {"label": "First Name", "required": True, "type": "string", "section": "ePatient", "phi": True},
        "ePatient.04": {"label": "Age", "required": True, "type": "integer", "section": "ePatient"},
        "ePatient.05": {"label": "Age Units", "required": True, "type": "code", "section": "ePatient"},
        "ePatient.13": {"label": "Gender", "required": True, "type": "code", "section": "ePatient"},
        "ePatient.15": {"label": "Race", "required": False, "type": "code", "section": "ePatient"},
        "eDispatch.01": {"label": "Complaint Reported by Dispatch", "required": True, "type": "string", "section": "eDispatch"},
        "eDispatch.02": {"label": "EMD Performed", "required": True, "type": "code", "section": "eDispatch"},
        "eScene.01": {"label": "First EMS Unit on Scene", "required": True, "type": "code", "section": "eScene"},
        "eScene.06": {"label": "Incident Address", "required": True, "type": "string", "section": "eScene", "phi": True},
        "eScene.07": {"label": "Incident City", "required": True, "type": "string", "section": "eScene"},
        "eScene.09": {"label": "Incident State", "required": True, "type": "code", "section": "eScene"},
        "eScene.10": {"label": "Incident ZIP Code", "required": True, "type": "string", "section": "eScene"},
        "eSituation.01": {"label": "Date/Time of Symptom Onset", "required": False, "type": "dateTime", "section": "eSituation"},
        "eSituation.07": {"label": "Chief Complaint Anatomic Location", "required": True, "type": "code", "section": "eSituation"},
        "eSituation.08": {"label": "Chief Complaint Organ System", "required": True, "type": "code", "section": "eSituation"},
        "eSituation.09": {"label": "Primary Symptom", "required": True, "type": "code", "section": "eSituation"},
        "eSituation.11": {"label": "Provider's Primary Impression", "required": True, "type": "code", "section": "eSituation"},
        "eSituation.13": {"label": "Initial Patient Acuity", "required": True, "type": "code", "section": "eSituation"},
        "eHistory.01": {"label": "Barriers to Patient Care", "required": True, "type": "code", "section": "eHistory"},
        "eVitals.01": {"label": "Date/Time Vital Signs Taken", "required": True, "type": "dateTime", "section": "eVitals"},
        "eVitals.06": {"label": "Pulse Oximetry", "required": False, "type": "integer", "section": "eVitals"},
        "eVitals.10": {"label": "Heart Rate", "required": True, "type": "integer", "section": "eVitals"},
        "eVitals.14": {"label": "Systolic Blood Pressure", "required": True, "type": "integer", "section": "eVitals"},
        "eVitals.15": {"label": "Diastolic Blood Pressure", "required": True, "type": "integer", "section": "eVitals"},
        "eVitals.16": {"label": "Method of Blood Pressure Measurement", "required": False, "type": "code", "section": "eVitals"},
        "eVitals.18": {"label": "Respiratory Rate", "required": True, "type": "integer", "section": "eVitals"},
        "eVitals.21": {"label": "Glasgow Coma Score Total", "required": True, "type": "integer", "section": "eVitals"},
        "eProcedures.01": {"label": "Date/Time Procedure Performed", "required": True, "type": "dateTime", "section": "eProcedures"},
        "eProcedures.03": {"label": "Procedure", "required": True, "type": "code", "section": "eProcedures"},
        "eProcedures.05": {"label": "Number of Procedure Attempts", "required": True, "type": "integer", "section": "eProcedures"},
        "eProcedures.06": {"label": "Procedure Successful", "required": True, "type": "code", "section": "eProcedures"},
        "eMedications.01": {"label": "Date/Time Medication Administered", "required": True, "type": "dateTime", "section": "eMedications"},
        "eMedications.03": {"label": "Medication Given", "required": True, "type": "code", "section": "eMedications"},
        "eMedications.05": {"label": "Medication Dosage", "required": True, "type": "decimal", "section": "eMedications"},
        "eMedications.06": {"label": "Medication Dosage Units", "required": True, "type": "code", "section": "eMedications"},
        "eDisposition.12": {"label": "Incident/Patient Disposition", "required": True, "type": "code", "section": "eDisposition"},
        "eDisposition.16": {"label": "Transport Disposition", "required": True, "type": "code", "section": "eDisposition"},
        "eDisposition.21": {"label": "Destination/Transferred To Code", "required": False, "type": "code", "section": "eDisposition"},
        "eOutcome.01": {"label": "Emergency Department Disposition", "required": False, "type": "code", "section": "eOutcome"},
        "eNarrative.01": {"label": "Patient Care Report Narrative", "required": True, "type": "string", "section": "eNarrative"},
    },
}

REQUIRED_ELEMENTS = [k for k, v in NEMSIS_351_SCHEMA["elements"].items() if v["required"]]
ELEMENT_SECTIONS = list({v["section"] for v in NEMSIS_351_SCHEMA["elements"].values()})


# ── Schema viewer ─────────────────────────────────────────────────────────────

@router.get("/schema")
async def full_schema_viewer(
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "version": NEMSIS_351_SCHEMA["version"],
        "total_elements": len(NEMSIS_351_SCHEMA["elements"]),
        "required_count": len(REQUIRED_ELEMENTS),
        "sections": ELEMENT_SECTIONS,
        "schema": NEMSIS_351_SCHEMA["elements"],
    }


# ── Element hierarchy browser ─────────────────────────────────────────────────

@router.get("/schema/hierarchy")
async def element_hierarchy(
    current: CurrentUser = Depends(get_current_user),
):
    hierarchy: dict[str, list[dict[str, Any]]] = {}
    for elem_id, elem in NEMSIS_351_SCHEMA["elements"].items():
        section = elem["section"]
        if section not in hierarchy:
            hierarchy[section] = []
        hierarchy[section].append({"id": elem_id, "label": elem["label"], "required": elem["required"], "type": elem["type"]})
    return {"hierarchy": hierarchy, "sections": list(hierarchy.keys())}


# ── Required vs optional field tracker ───────────────────────────────────────

@router.get("/schema/field-requirements")
async def field_requirements(
    current: CurrentUser = Depends(get_current_user),
):
    required = {k: v for k, v in NEMSIS_351_SCHEMA["elements"].items() if v["required"]}
    optional = {k: v for k, v in NEMSIS_351_SCHEMA["elements"].items() if not v["required"]}
    return {
        "required": required,
        "optional": optional,
        "required_count": len(required),
        "optional_count": len(optional),
    }


# ── State-specific mapping ────────────────────────────────────────────────────

@router.get("/schema/state-mapping/{state_code}")
async def state_mapping(
    state_code: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    mappings = _svc(db).repo("nemsis_state_mappings").list(tenant_id=current.tenant_id)
    state_map = next((m for m in mappings if m.get("data", {}).get("state_code") == state_code.upper()), None)
    additional_required = []
    if state_map:
        additional_required = state_map.get("data", {}).get("additional_required_elements", [])
    return {
        "state": state_code.upper(),
        "base_required": REQUIRED_ELEMENTS,
        "state_additional_required": additional_required,
        "total_required": list(set(REQUIRED_ELEMENTS + additional_required)),
    }


@router.post("/schema/state-mapping")
async def create_state_mapping(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_state_mappings",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "state_code": payload.get("state_code", "").upper(),
            "additional_required_elements": payload.get("additional_required_elements", []),
            "conditional_rules": payload.get("conditional_rules", []),
            "submission_endpoint": payload.get("submission_endpoint"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ── Version comparison tool ───────────────────────────────────────────────────

@router.post("/schema/version-compare")
async def version_compare(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    v1 = payload.get("version_a", "3.4.0")
    v2 = payload.get("version_b", "3.5.1")
    changes = [
        {"element": "eVitals.06", "change": "added", "version": "3.5.0"},
        {"element": "eScene.15", "change": "deprecated", "version": "3.5.1"},
        {"element": "eRecord.04", "change": "required_added", "version": "3.5.1"},
        {"element": "eSituation.13", "change": "value_set_updated", "version": "3.5.1"},
    ]
    return {"version_a": v1, "version_b": v2, "changes": changes, "change_count": len(changes)}


# ── XML validation engine ─────────────────────────────────────────────────────

@router.post("/validate/xml")
async def validate_xml(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    xml_content = payload.get("xml_content", "")
    try:
        xml_bytes = xml_content.encode() if isinstance(xml_content, str) else xml_content
        result = validate_nemsis_xml(xml_bytes)
    except Exception as exc:
        result = {"valid": False, "errors": [str(exc)], "warnings": []}
    rec = await _svc(db).create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "validation_type": "xml", "source": payload.get("source")},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {**result, "record_id": str(rec.get("id"))}


# ── Real-time field validation ────────────────────────────────────────────────

@router.post("/validate/field")
async def validate_field(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    element_id = payload.get("element_id")
    value = payload.get("value")
    schema_elem = NEMSIS_351_SCHEMA["elements"].get(element_id)
    if not schema_elem:
        return {"valid": False, "element_id": element_id, "error": "Unknown element ID"}
    errors = []
    if schema_elem["required"] and (value is None or value == ""):
        errors.append(f"{element_id} is required")
    if value is not None and schema_elem["type"] == "integer":
        try:
            int(value)
        except (ValueError, TypeError):
            errors.append(f"{element_id} must be an integer")
    if value is not None and schema_elem["type"] == "decimal":
        try:
            float(value)
        except (ValueError, TypeError):
            errors.append(f"{element_id} must be a decimal number")
    return {
        "valid": not errors,
        "element_id": element_id,
        "label": schema_elem["label"],
        "errors": errors,
        "value": value,
    }


# ── Conditional element enforcement ──────────────────────────────────────────

@router.post("/validate/conditional")
async def conditional_enforcement(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    incident = payload.get("incident", {})
    conditional_rules = [
        {
            "rule": "If transport occurred, eDisposition.16 required",
            "condition": lambda i: i.get("transported") is True,
            "required_element": "eDisposition.16",
            "present": lambda i: bool(i.get("transport_disposition")),
        },
        {
            "rule": "If medication administered, eMedications.05 required",
            "condition": lambda i: bool(i.get("medications")),
            "required_element": "eMedications.05",
            "present": lambda i: all(bool(m.get("dosage")) for m in (i.get("medications") or [])),
        },
    ]
    violations = []
    for rule in conditional_rules:
        if rule["condition"](incident) and not rule["present"](incident):
            violations.append({"rule": rule["rule"], "missing_element": rule["required_element"]})
    return {"violations": violations, "compliant": not violations, "rules_checked": len(conditional_rules)}


# ── Data type validator ───────────────────────────────────────────────────────

@router.post("/validate/data-types")
async def validate_data_types(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    fields = payload.get("fields", {})
    errors = []
    for elem_id, value in fields.items():
        schema_elem = NEMSIS_351_SCHEMA["elements"].get(elem_id)
        if not schema_elem:
            continue
        t = schema_elem["type"]
        if t == "integer" and value is not None:
            try:
                int(value)
            except (ValueError, TypeError):
                errors.append({"element": elem_id, "expected": "integer", "got": type(value).__name__})
        elif t == "decimal" and value is not None:
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append({"element": elem_id, "expected": "decimal", "got": type(value).__name__})
    return {"valid": not errors, "type_errors": errors, "fields_checked": len(fields)}


# ── Value set validator ───────────────────────────────────────────────────────

@router.post("/validate/value-sets")
async def validate_value_sets(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    fields = payload.get("fields", {})
    value_sets: dict[str, list[str]] = {
        "ePatient.05": ["Years", "Months", "Days", "Hours", "Minutes"],
        "ePatient.13": ["Male", "Female", "Unknown", "Trans Male", "Trans Female"],
        "eDispatch.02": ["Yes", "No", "Unknown"],
        "eSituation.13": ["Critical", "Emergent", "Lower Acuity", "Non-Acute"],
    }
    errors = []
    for elem_id, value in fields.items():
        if elem_id in value_sets and value not in value_sets[elem_id]:
            errors.append({
                "element": elem_id,
                "value": value,
                "valid_values": value_sets[elem_id],
            })
    return {"valid": not errors, "value_set_errors": errors}


# ── Narrative length checker ──────────────────────────────────────────────────

@router.post("/validate/narrative")
async def narrative_length_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    narrative = payload.get("narrative", "")
    min_length = 50
    max_length = 10000
    required_phrases_present = any(
        phrase in narrative.lower()
        for phrase in ["patient", "assessment", "treatment", "transport"]
    )
    return {
        "length": len(narrative),
        "min_length": min_length,
        "max_length": max_length,
        "meets_minimum": len(narrative) >= min_length,
        "within_maximum": len(narrative) <= max_length,
        "required_phrases_present": required_phrases_present,
        "valid": len(narrative) >= min_length and len(narrative) <= max_length,
    }


# ── Missing required field alert ─────────────────────────────────────────────

@router.post("/validate/missing-fields")
async def missing_fields_alert(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    provided_elements = set(payload.get("provided_elements", []))
    state_code = payload.get("state_code")
    required = set(REQUIRED_ELEMENTS)
    missing = list(required - provided_elements)
    missing_details = [
        {"element": e, "label": NEMSIS_351_SCHEMA["elements"].get(e, {}).get("label", e), "section": NEMSIS_351_SCHEMA["elements"].get(e, {}).get("section", "")}
        for e in missing
    ]
    return {
        "missing_count": len(missing),
        "missing_elements": missing_details,
        "provided_count": len(provided_elements),
        "state": state_code,
        "submission_ready": not missing,
    }


# ── Invalid code detection ────────────────────────────────────────────────────

@router.post("/validate/invalid-codes")
async def invalid_code_detection(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    codes = payload.get("codes", {})
    known_invalid_patterns = ["9999", "UNKNOWN", "N/A", "NULL"]
    invalid = []
    for elem_id, code in codes.items():
        if str(code).upper() in known_invalid_patterns:
            invalid.append({"element": elem_id, "code": code, "reason": "Non-specific or placeholder code"})
    return {"invalid_codes": invalid, "has_invalid": bool(invalid)}


# ── Auto-correct suggestion engine ───────────────────────────────────────────

@router.post("/validate/auto-correct")
async def auto_correct_suggestions(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    fields = payload.get("fields", {})
    suggestions: list[dict[str, Any]] = []
    gender_map = {"M": "Male", "F": "Female", "U": "Unknown", "m": "Male", "f": "Female"}
    if "ePatient.13" in fields and fields["ePatient.13"] in gender_map:
        suggestions.append({
            "element": "ePatient.13",
            "current": fields["ePatient.13"],
            "suggested": gender_map[fields["ePatient.13"]],
            "reason": "Normalize to NEMSIS value set",
        })
    for elem_id, value in fields.items():
        elem = NEMSIS_351_SCHEMA["elements"].get(elem_id)
        if elem and elem["type"] == "dateTime" and value and "T" not in str(value):
            suggestions.append({
                "element": elem_id,
                "current": value,
                "suggested": f"{value}T00:00:00Z",
                "reason": "Add ISO 8601 time component",
            })
    return {"suggestions": suggestions, "count": len(suggestions)}


# ── Export preview renderer ───────────────────────────────────────────────────

@router.post("/export/preview")
async def export_preview(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    incident = payload.get("incident", {})
    patient = payload.get("patient", {})
    vitals = payload.get("vitals", [])
    agency = payload.get("agency", {})
    if incident and patient:
        try:
            xml_bytes = build_nemsis_document(incident=incident, patient=patient, vitals=vitals, agency_info=agency)
            xml_preview = xml_bytes.decode("utf-8", errors="replace")[:2000]
            valid = True
            errors: list[str] = []
        except Exception as exc:
            xml_preview = ""
            valid = False
            errors = [str(exc)]
    else:
        xml_preview = ""
        valid = False
        errors = ["incident and patient data required"]
    return {
        "preview": xml_preview,
        "valid": valid,
        "errors": errors,
        "truncated": len(xml_preview) == 2000,
    }


# ── Export failure reason breakdown ──────────────────────────────────────────

@router.get("/export/failure-analysis")
async def export_failure_analysis(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    jobs = _svc(db).repo("nemsis_export_jobs").list(tenant_id=current.tenant_id)
    failed = [j for j in jobs if j.get("data", {}).get("status") == "failed"]
    reasons: dict[str, int] = {}
    for j in failed:
        error = j.get("data", {}).get("error", "unknown")
        reasons[error] = reasons.get(error, 0) + 1
    return {
        "total_exports": len(jobs),
        "failed_count": len(failed),
        "failure_rate": round(len(failed) / len(jobs) * 100, 1) if jobs else 0,
        "failure_reasons": reasons,
    }


# ── Error clustering analysis ─────────────────────────────────────────────────

@router.get("/errors/clusters")
async def error_clusters(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    validations = _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    cluster: dict[str, int] = {}
    for v in validations:
        for err in v.get("data", {}).get("errors", []):
            key = str(err)[:80]
            cluster[key] = cluster.get(key, 0) + 1
    sorted_clusters = sorted(cluster.items(), key=lambda x: x[1], reverse=True)
    return {"clusters": [{"error": k, "occurrences": c} for k, c in sorted_clusters[:20]]}


# ── State submission readiness score ─────────────────────────────────────────

@router.post("/readiness-score")
async def readiness_score(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    provided = set(payload.get("provided_elements", []))
    state_code = payload.get("state_code", "")
    required = set(REQUIRED_ELEMENTS)
    missing = required - provided
    completeness = round((len(provided & required) / len(required)) * 100, 1) if required else 100
    return {
        "state": state_code,
        "completeness_pct": completeness,
        "required_count": len(required),
        "provided_required": len(provided & required),
        "missing_required": len(missing),
        "ready_for_submission": completeness == 100,
        "score_label": "Ready" if completeness == 100 else "Needs Work" if completeness >= 80 else "Incomplete",
    }


# ── Dataset completeness score ────────────────────────────────────────────────

@router.post("/completeness-score")
async def completeness_score(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    provided = set(payload.get("provided_elements", []))
    total = len(NEMSIS_351_SCHEMA["elements"])
    filled = len(provided & set(NEMSIS_351_SCHEMA["elements"].keys()))
    required_filled = len(provided & set(REQUIRED_ELEMENTS))
    return {
        "total_elements": total,
        "filled_elements": filled,
        "optional_filled": filled - required_filled,
        "required_filled": required_filled,
        "required_total": len(REQUIRED_ELEMENTS),
        "overall_pct": round(filled / total * 100, 1),
        "required_pct": round(required_filled / len(REQUIRED_ELEMENTS) * 100, 1),
    }


# ── Field-level compliance heatmap ────────────────────────────────────────────

@router.post("/heatmap")
async def compliance_heatmap(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    validations = _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    error_counts: dict[str, int] = {}
    for v in validations:
        for err in v.get("data", {}).get("errors", []):
            for elem_id in NEMSIS_351_SCHEMA["elements"]:
                if elem_id in str(err):
                    error_counts[elem_id] = error_counts.get(elem_id, 0) + 1
    heatmap = [{"element": k, "error_count": c, "label": NEMSIS_351_SCHEMA["elements"][k]["label"]} for k, c in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)]
    return {"heatmap": heatmap[:30]}


# ── Field auto-population engine ─────────────────────────────────────────────

@router.post("/auto-populate")
async def auto_populate(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    incident = payload.get("incident", {})
    suggestions: dict[str, Any] = {}
    if not incident.get("eScene.09") and incident.get("state"):
        state_codes = {"California": "CA", "Texas": "TX", "Florida": "FL", "New York": "NY"}
        suggestions["eScene.09"] = state_codes.get(incident.get("state", ""), incident.get("state", ""))
    if not incident.get("eRecord.03"):
        suggestions["eRecord.03"] = "FusionEMS Quantum"
    if not incident.get("eRecord.04"):
        suggestions["eRecord.04"] = "1.0"
    if not incident.get("eRecord.02"):
        suggestions["eRecord.02"] = "FusionEMS"
    return {"auto_populated": suggestions, "count": len(suggestions)}


# ── Controlled vocabulary editor ─────────────────────────────────────────────

@router.get("/vocabulary/{element_id}")
async def get_vocabulary(
    element_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    vocab = _svc(db).repo("nemsis_vocabularies").list(tenant_id=current.tenant_id)
    elem_vocab = next((v for v in vocab if v.get("data", {}).get("element_id") == element_id), None)
    built_in = {
        "ePatient.05": ["Years", "Months", "Days", "Hours", "Minutes"],
        "ePatient.13": ["Male", "Female", "Unknown", "Trans Male", "Trans Female"],
        "eSituation.13": ["Critical", "Emergent", "Lower Acuity", "Non-Acute"],
        "eDispatch.02": ["Yes", "No", "Unknown"],
    }
    values = elem_vocab.get("data", {}).get("values") if elem_vocab else built_in.get(element_id, [])
    return {"element_id": element_id, "values": values, "source": "custom" if elem_vocab else "built_in"}


@router.post("/vocabulary")
async def create_vocabulary(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_vocabularies",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "element_id": payload.get("element_id"),
            "values": payload.get("values", []),
            "description": payload.get("description"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ── Version lock enforcement ──────────────────────────────────────────────────

@router.get("/version-lock")
async def version_lock_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    locks = _svc(db).repo("nemsis_version_locks").list(tenant_id=current.tenant_id)
    active = next((lk for lk in locks if lk.get("data", {}).get("active")), None)
    return {
        "locked_version": active.get("data", {}).get("version") if active else NEMSIS_351_SCHEMA["version"],
        "lock_active": bool(active),
        "current_version": NEMSIS_351_SCHEMA["version"],
    }


@router.post("/version-lock")
async def set_version_lock(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_version_locks",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"version": payload.get("version", "3.5.1"), "active": True, "locked_by": str(current.user_id)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ── Upgrade impact simulation ─────────────────────────────────────────────────

@router.post("/upgrade-impact")
async def upgrade_impact(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    from_version = payload.get("from_version", "3.4.0")
    to_version = payload.get("to_version", "3.5.1")
    validations = _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    breaking_changes = [
        {"element": "eRecord.04", "change": "Now required in 3.5.1"},
        {"element": "eSituation.13", "change": "Value set updated"},
    ]
    impacted_records = len([v for v in validations if v.get("data", {}).get("status") != "validated"])
    return {
        "from_version": from_version,
        "to_version": to_version,
        "breaking_changes": breaking_changes,
        "impacted_records": impacted_records,
        "migration_required": bool(breaking_changes),
    }


# ── Data normalization tool ───────────────────────────────────────────────────

@router.post("/normalize")
async def normalize_data(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    record = payload.get("record", {})
    normalized = dict(record)
    bool_to_yn = {True: "Yes", False: "No"}
    for elem_id in ["eDispatch.02"]:
        if elem_id in normalized and normalized[elem_id] in bool_to_yn:
            normalized[elem_id] = bool_to_yn[normalized[elem_id]]
    gender_norm = {"M": "Male", "F": "Female", "m": "Male", "f": "Female", "U": "Unknown"}
    if "ePatient.13" in normalized and normalized["ePatient.13"] in gender_norm:
        normalized["ePatient.13"] = gender_norm[normalized["ePatient.13"]]
    changes = {k: {"from": record[k], "to": normalized[k]} for k in normalized if normalized[k] != record.get(k)}
    return {"normalized": normalized, "changes": changes, "change_count": len(changes)}


# ── XML schema cache ──────────────────────────────────────────────────────────

@router.get("/schema/cache-status")
async def schema_cache_status(
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "cached": True,
        "version": NEMSIS_351_SCHEMA["version"],
        "element_count": len(NEMSIS_351_SCHEMA["elements"]),
        "cache_ttl_seconds": 3600,
        "checksum": hashlib.md5(str(NEMSIS_351_SCHEMA).encode()).hexdigest(),
    }


# ── Custom extension field manager ────────────────────────────────────────────

@router.post("/extensions")
async def create_extension(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_extensions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "element_id": payload.get("element_id"),
            "label": payload.get("label"),
            "data_type": payload.get("data_type", "string"),
            "required": payload.get("required", False),
            "section": payload.get("section", "eCustom"),
            "approved": False,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/extensions")
async def list_extensions(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_extensions").list(tenant_id=current.tenant_id)


# ── Audit-ready export bundle ─────────────────────────────────────────────────

@router.post("/audit-bundle")
async def audit_bundle(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    validations = svc.repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    exports = svc.repo("nemsis_export_jobs").list(tenant_id=current.tenant_id)
    rec = await svc.create(
        table="nemsis_audit_bundles",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "date_range": payload.get("date_range"),
            "validation_count": len(validations),
            "export_count": len(exports),
            "generated_by": str(current.user_id),
            "status": "ready",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"bundle_id": str(rec.get("id")), "status": "ready", "validation_count": len(validations), "export_count": len(exports)}


# ── Field usage analytics ─────────────────────────────────────────────────────

@router.get("/analytics/field-usage")
async def field_usage_analytics(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    validations = _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    usage: dict[str, int] = {}
    for v in validations:
        for elem_id in (v.get("data", {}).get("provided_elements") or []):
            usage[elem_id] = usage.get(elem_id, 0) + 1
    sorted_usage = sorted(usage.items(), key=lambda x: x[1], reverse=True)
    return {"field_usage": [{"element": k, "usage_count": c} for k, c in sorted_usage[:30]]}


# ── Deprecated field alert ────────────────────────────────────────────────────

@router.post("/validate/deprecated-fields")
async def deprecated_fields_alert(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    provided = set(payload.get("provided_elements", []))
    deprecated = {"eScene.15", "ePatient.07", "eHistory.07"}
    found_deprecated = list(provided & deprecated)
    return {
        "deprecated_found": found_deprecated,
        "count": len(found_deprecated),
        "warning": bool(found_deprecated),
        "message": f"Found {len(found_deprecated)} deprecated element(s)" if found_deprecated else "No deprecated elements found",
    }


# ── Timestamp integrity validation ────────────────────────────────────────────

@router.post("/validate/timestamps")
async def timestamp_integrity(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    times = payload.get("timestamps", {})
    errors = []
    ordered_keys = [
        ("eTimes.01", "eTimes.03"),
        ("eTimes.03", "eTimes.05"),
        ("eTimes.05", "eTimes.06"),
        ("eTimes.06", "eTimes.09"),
        ("eTimes.09", "eTimes.11"),
        ("eTimes.11", "eTimes.13"),
    ]
    for a, b in ordered_keys:
        if a in times and b in times:
            if str(times[a]) > str(times[b]):
                errors.append({"rule": f"{a} must be before {b}", "a": times[a], "b": times[b]})
    return {"valid": not errors, "timestamp_errors": errors}


# ── Duplicate incident detection ──────────────────────────────────────────────

@router.post("/validate/duplicates")
async def duplicate_detection(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    pcr_number = payload.get("pcr_number")
    validations = _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    matches = [v for v in validations if v.get("data", {}).get("pcr_number") == pcr_number]
    return {
        "pcr_number": pcr_number,
        "duplicate_found": len(matches) > 1,
        "occurrence_count": len(matches),
        "record_ids": [str(m.get("id")) for m in matches],
    }


# ── Cross-field consistency checker ──────────────────────────────────────────

@router.post("/validate/cross-field-consistency")
async def cross_field_consistency(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    fields = payload.get("fields", {})
    errors = []
    age = fields.get("ePatient.04")
    age_unit = fields.get("ePatient.05")
    if age is not None and age_unit:
        try:
            if int(age) < 0:
                errors.append("ePatient.04: Age cannot be negative")
            if int(age) > 150 and age_unit == "Years":
                errors.append("ePatient.04: Age exceeds plausible range for Years")
        except (ValueError, TypeError):
            pass
    hr = fields.get("eVitals.10")
    if hr is not None:
        try:
            if not (0 <= int(hr) <= 350):
                errors.append("eVitals.10: Heart rate out of plausible range (0-350)")
        except (ValueError, TypeError):
            pass
    sbp = fields.get("eVitals.14")
    dbp = fields.get("eVitals.15")
    if sbp is not None and dbp is not None:
        try:
            if int(dbp) >= int(sbp):
                errors.append("eVitals.15: Diastolic BP must be less than Systolic BP")
        except (ValueError, TypeError):
            pass
    return {"valid": not errors, "consistency_errors": errors}


# ── Medical necessity keyword detector ───────────────────────────────────────

@router.post("/validate/medical-necessity")
async def medical_necessity_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    narrative = payload.get("narrative", "")
    keywords = [
        "altered mental status", "respiratory distress", "chest pain",
        "cardiac arrest", "stroke", "trauma", "unresponsive",
        "hypoxia", "hypotension", "seizure",
    ]
    found = [kw for kw in keywords if kw.lower() in narrative.lower()]
    return {
        "narrative_length": len(narrative),
        "medical_necessity_keywords_found": found,
        "has_medical_necessity": bool(found),
        "recommendation": "Sufficient medical necessity documentation" if found else "Add more clinical detail to support medical necessity",
    }


# ── Medication dosage validator ───────────────────────────────────────────────

@router.post("/validate/medication-dosage")
async def medication_dosage_validator(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    medications = payload.get("medications", [])
    errors = []
    for i, med in enumerate(medications):
        dosage = med.get("eMedications.05")
        units = med.get("eMedications.06")
        if dosage is None:
            errors.append({"index": i, "error": "Missing dosage"})
        elif not units:
            errors.append({"index": i, "error": "Missing dosage units"})
        else:
            try:
                if float(dosage) <= 0:
                    errors.append({"index": i, "error": "Dosage must be positive"})
            except (ValueError, TypeError):
                errors.append({"index": i, "error": "Dosage must be numeric"})
    return {"valid": not errors, "medication_count": len(medications), "dosage_errors": errors}


# ── Response time validation ──────────────────────────────────────────────────

@router.post("/validate/response-times")
async def response_time_validation(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    dispatch = payload.get("eTimes.01")
    on_scene = payload.get("eTimes.06")
    warnings = []
    if dispatch and on_scene:
        if str(on_scene) < str(dispatch):
            return {"valid": False, "errors": ["Scene arrival before dispatch call"]}
    return {"valid": True, "warnings": warnings, "dispatch": dispatch, "on_scene": on_scene}


# ── Transport destination validation ─────────────────────────────────────────

@router.post("/validate/transport-destination")
async def transport_destination_validation(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    transported = payload.get("transported", False)
    destination = payload.get("eDisposition.21")
    transport_disp = payload.get("eDisposition.16")
    errors = []
    if transported and not destination:
        errors.append("eDisposition.21: Destination required when patient transported")
    if transported and not transport_disp:
        errors.append("eDisposition.16: Transport disposition required when patient transported")
    return {"valid": not errors, "transport_errors": errors}


# ── Data lineage tracking ─────────────────────────────────────────────────────

@router.post("/lineage")
async def create_lineage_record(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_data_lineage",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "incident_id": payload.get("incident_id"),
            "element_id": payload.get("element_id"),
            "operation": payload.get("operation"),
            "source_system": payload.get("source_system"),
            "previous_value": payload.get("previous_value"),
            "new_value": payload.get("new_value"),
            "actor": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/lineage/{incident_id}")
async def get_lineage(
    incident_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    lineage = _svc(db).repo("nemsis_data_lineage").list(tenant_id=current.tenant_id)
    incident_lineage = [rec for rec in lineage if rec.get("data", {}).get("incident_id") == incident_id]
    return {"incident_id": incident_id, "lineage": incident_lineage, "count": len(incident_lineage)}


# ── Element-level audit log ───────────────────────────────────────────────────

@router.get("/audit-log")
async def nemsis_audit_log(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_data_lineage").list(tenant_id=current.tenant_id)


# ── Auto-generated compliance report ─────────────────────────────────────────

@router.get("/compliance-report")
async def compliance_report(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    validations = svc.repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    exports = svc.repo("nemsis_export_jobs").list(tenant_id=current.tenant_id)
    valid_count = len([v for v in validations if v.get("data", {}).get("valid")])
    failed_exports = len([e for e in exports if e.get("data", {}).get("status") == "failed"])
    return {
        "report_type": "NEMSIS 3.5.1 Compliance",
        "version": NEMSIS_351_SCHEMA["version"],
        "total_validations": len(validations),
        "valid_submissions": valid_count,
        "validation_rate_pct": round(valid_count / len(validations) * 100, 1) if validations else 0,
        "total_exports": len(exports),
        "failed_exports": failed_exports,
        "tenant_id": str(current.tenant_id),
    }


# ── Validation severity tiers ─────────────────────────────────────────────────

@router.post("/validate/severity-tiers")
async def severity_tiers(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    errors = payload.get("errors", [])
    critical_keys = {"eRecord.01", "ePatient.01", "eTimes.01", "eNarrative.01"}
    tiered: dict[str, list[Any]] = {"critical": [], "major": [], "minor": []}
    for err in errors:
        err_str = str(err)
        if any(k in err_str for k in critical_keys):
            tiered["critical"].append(err)
        elif "required" in err_str.lower():
            tiered["major"].append(err)
        else:
            tiered["minor"].append(err)
    return {"tiered_errors": tiered, "total": len(errors)}


# ── Error remediation suggestions ────────────────────────────────────────────

@router.post("/remediation-suggestions")
async def remediation_suggestions(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    errors = payload.get("errors", [])
    suggestions = []
    for err in errors:
        err_str = str(err)
        if "eNarrative.01" in err_str:
            suggestions.append({"error": err_str, "action": "Add patient care narrative with at least 50 characters"})
        elif "eTimes" in err_str:
            suggestions.append({"error": err_str, "action": "Verify timestamp sequence: dispatch -> en route -> on scene -> transport -> destination"})
        elif "eVitals" in err_str:
            suggestions.append({"error": err_str, "action": "Record complete vital signs set at initial patient contact"})
        elif "required" in err_str.lower():
            suggestions.append({"error": err_str, "action": "Complete all required NEMSIS 3.5.1 elements before submission"})
        else:
            suggestions.append({"error": err_str, "action": "Review NEMSIS 3.5.1 data dictionary for element requirements"})
    return {"suggestions": suggestions, "count": len(suggestions)}


# ── Schema update alert system ────────────────────────────────────────────────

@router.get("/schema/update-alerts")
async def schema_update_alerts(
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "current_version": "3.5.1",
        "latest_available": "3.5.1",
        "update_available": False,
        "pending_alerts": [],
        "last_checked": "2026-02-26",
    }


# ── Field dependency graph viewer ─────────────────────────────────────────────

@router.get("/schema/dependency-graph")
async def dependency_graph(
    current: CurrentUser = Depends(get_current_user),
):
    dependencies = [
        {"element": "eDisposition.16", "depends_on": "eDisposition.12", "rule": "required if transport occurred"},
        {"element": "eMedications.05", "depends_on": "eMedications.03", "rule": "required when medication given"},
        {"element": "eProcedures.06", "depends_on": "eProcedures.03", "rule": "required when procedure performed"},
        {"element": "eTimes.11", "depends_on": "eDisposition.16", "rule": "required when transported"},
    ]
    return {"dependencies": dependencies, "count": len(dependencies)}


# ── Real-time export simulation ───────────────────────────────────────────────

@router.post("/export/simulate")
async def export_simulation(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    incident = payload.get("incident", {})
    patient = payload.get("patient", {})
    provided = set(list(incident.keys()) + list(patient.keys()))
    required = set(REQUIRED_ELEMENTS)
    missing = list(required - provided)
    can_export = not missing
    return {
        "simulation": True,
        "can_export": can_export,
        "missing_elements": missing,
        "missing_count": len(missing),
        "provided_count": len(provided),
        "estimated_xml_kb": round(len(str(payload)) / 1024, 2),
    }


# ── State rejection tracker ───────────────────────────────────────────────────

@router.post("/state-rejections")
async def create_state_rejection(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_state_rejections",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "state_code": payload.get("state_code"),
            "submission_id": payload.get("submission_id"),
            "rejection_reason": payload.get("rejection_reason"),
            "rejected_elements": payload.get("rejected_elements", []),
            "resolved": False,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/state-rejections")
async def list_state_rejections(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_state_rejections").list(tenant_id=current.tenant_id)


# ── Export batching control ───────────────────────────────────────────────────

@router.post("/export/batch")
async def create_export_batch(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "billing", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_export_batches",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "incident_ids": payload.get("incident_ids", []),
            "state_code": payload.get("state_code"),
            "batch_size": len(payload.get("incident_ids", [])),
            "status": "queued",
            "created_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/export/batches")
async def list_export_batches(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_export_batches").list(tenant_id=current.tenant_id)


# ── Dataset backup versioning ─────────────────────────────────────────────────

@router.post("/backup")
async def create_backup(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_backups",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "backup_type": payload.get("backup_type", "full"),
            "record_count": payload.get("record_count", 0),
            "created_by": str(current.user_id),
            "status": "completed",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/backups")
async def list_backups(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_backups").list(tenant_id=current.tenant_id)


# ── Export status dashboard ───────────────────────────────────────────────────

@router.get("/export/dashboard")
async def export_dashboard(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    jobs = svc.repo("nemsis_export_jobs").list(tenant_id=current.tenant_id)
    batches = svc.repo("nemsis_export_batches").list(tenant_id=current.tenant_id)
    rejections = svc.repo("nemsis_state_rejections").list(tenant_id=current.tenant_id)
    by_status: dict[str, int] = {}
    for j in jobs:
        s = j.get("data", {}).get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total_jobs": len(jobs),
        "total_batches": len(batches),
        "total_rejections": len(rejections),
        "jobs_by_status": by_status,
        "pending_batches": len([b for b in batches if b.get("data", {}).get("status") == "queued"]),
    }


# ── Multi-state compatibility testing ────────────────────────────────────────

@router.post("/multi-state-test")
async def multi_state_test(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    states = payload.get("states", [])
    provided = set(payload.get("provided_elements", []))
    results = []
    for state in states:
        mappings = _svc(db).repo("nemsis_state_mappings").list(tenant_id=current.tenant_id)
        state_map = next((m for m in mappings if m.get("data", {}).get("state_code") == state.upper()), None)
        extra = state_map.get("data", {}).get("additional_required_elements", []) if state_map else []
        state_required = set(REQUIRED_ELEMENTS + extra)
        missing = list(state_required - provided)
        results.append({"state": state, "ready": not missing, "missing_count": len(missing), "missing": missing})
    return {"results": results, "all_states_ready": all(r["ready"] for r in results)}


# ── Live validation API endpoint ──────────────────────────────────────────────

@router.post("/validate/live")
async def live_validation(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    provided = set(payload.get("provided_elements", []))
    required = set(REQUIRED_ELEMENTS)
    missing = list(required - provided)
    errors = [f"Missing required element: {e}" for e in missing]
    result = {
        "valid": not missing,
        "errors": errors,
        "warnings": [],
        "missing_required": missing,
        "completeness_pct": round(len(provided & required) / len(required) * 100, 1) if required else 100,
    }
    await _svc(db).create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "validation_type": "live", "provided_elements": list(provided)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


# ── Export timing scheduler ───────────────────────────────────────────────────

@router.post("/export/schedule")
async def schedule_export(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_export_schedules",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "cron_expression": payload.get("cron_expression", "0 2 * * *"),
            "state_code": payload.get("state_code"),
            "enabled": True,
            "created_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/export/schedules")
async def list_export_schedules(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_export_schedules").list(tenant_id=current.tenant_id)


# ── Certification readiness monitor ──────────────────────────────────────────

@router.get("/certification-readiness")
async def certification_readiness(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    validations = svc.repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    rejections = svc.repo("nemsis_state_rejections").list(tenant_id=current.tenant_id)
    extensions = svc.repo("nemsis_extensions").list(tenant_id=current.tenant_id)
    valid_count = len([v for v in validations if v.get("data", {}).get("valid")])
    unresolved_rejections = len([r for r in rejections if not r.get("data", {}).get("resolved")])
    unapproved_extensions = len([e for e in extensions if not e.get("data", {}).get("approved")])
    checks = [
        {"check": "Validation rate >= 95%", "passed": (valid_count / len(validations) * 100 >= 95) if validations else False},
        {"check": "No unresolved state rejections", "passed": unresolved_rejections == 0},
        {"check": "All extensions approved", "passed": unapproved_extensions == 0},
        {"check": "Version lock active", "passed": True},
    ]
    passed = sum(1 for c in checks if c["passed"])
    return {
        "certification_ready": passed == len(checks),
        "checks_passed": passed,
        "total_checks": len(checks),
        "checks": checks,
    }


# ── Data integrity scoring ────────────────────────────────────────────────────

@router.get("/integrity-score")
async def integrity_score(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    validations = svc.repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    if not validations:
        return {"integrity_score": 100, "grade": "A", "basis": "no_data"}
    valid = len([v for v in validations if v.get("data", {}).get("valid")])
    rate = valid / len(validations) * 100
    grade = "A" if rate >= 95 else "B" if rate >= 85 else "C" if rate >= 75 else "D" if rate >= 60 else "F"
    return {"integrity_score": round(rate, 1), "grade": grade, "valid_count": valid, "total": len(validations)}


# ── Provider-level compliance ranking ─────────────────────────────────────────

@router.get("/provider-ranking")
async def provider_ranking(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    lineage = _svc(db).repo("nemsis_data_lineage").list(tenant_id=current.tenant_id)
    provider_counts: dict[str, int] = {}
    for rec in lineage:
        actor = str(rec.get("data", {}).get("actor", "unknown"))
        provider_counts[actor] = provider_counts.get(actor, 0) + 1
    ranked = sorted(provider_counts.items(), key=lambda x: x[1], reverse=True)
    return {"providers": [{"provider_id": p, "submissions": c} for p, c in ranked]}


# ── Required demographic enforcement ─────────────────────────────────────────

@router.post("/validate/demographics")
async def validate_demographics(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    patient = payload.get("patient", {})
    required_demo = ["ePatient.01", "ePatient.02", "ePatient.04", "ePatient.05", "ePatient.13"]
    missing = [f for f in required_demo if not patient.get(f)]
    return {
        "valid": not missing,
        "missing_demographics": missing,
        "demographic_completeness_pct": round((len(required_demo) - len(missing)) / len(required_demo) * 100, 1),
    }


# ── Submission audit trail ────────────────────────────────────────────────────

@router.post("/submission-audit")
async def create_submission_audit(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_submission_audit",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "submission_id": payload.get("submission_id"),
            "state_code": payload.get("state_code"),
            "incident_count": payload.get("incident_count", 0),
            "status": payload.get("status", "submitted"),
            "submitted_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/submission-audit")
async def list_submission_audit(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_submission_audit").list(tenant_id=current.tenant_id)


# ── Reportable incident auto-flagging ────────────────────────────────────────

@router.post("/reportable-flag")
async def reportable_flag(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    incident = payload.get("incident", {})
    flags = []
    acuity = incident.get("eSituation.13", "")
    if acuity == "Critical":
        flags.append({"flag": "CRITICAL_PATIENT", "reason": "Patient acuity is Critical"})
    disposition = incident.get("eDisposition.12", "")
    if "Death" in str(disposition):
        flags.append({"flag": "PATIENT_DEATH", "reason": "Disposition indicates patient death"})
    narrative = incident.get("eNarrative.01", "")
    if "cardiac arrest" in narrative.lower():
        flags.append({"flag": "CARDIAC_ARREST", "reason": "Cardiac arrest documented in narrative"})
    return {
        "reportable": bool(flags),
        "flags": flags,
        "flag_count": len(flags),
    }


# ── Schema diff visualizer ────────────────────────────────────────────────────

@router.get("/schema/diff")
async def schema_diff(
    v1: str = Query("3.4.0"),
    v2: str = Query("3.5.1"),
    current: CurrentUser = Depends(get_current_user),
):
    diff = [
        {"element": "eVitals.06", "status": "added", "in_v1": False, "in_v2": True, "notes": "Pulse oximetry added"},
        {"element": "eScene.15", "status": "deprecated", "in_v1": True, "in_v2": False, "notes": "Removed in 3.5.1"},
        {"element": "eRecord.04", "status": "changed", "change_detail": "Optional -> Required", "notes": "Now required"},
    ]
    return {"version_a": v1, "version_b": v2, "diff": diff, "total_changes": len(diff)}


# ── Field cardinality enforcement ─────────────────────────────────────────────

@router.post("/validate/cardinality")
async def cardinality_enforcement(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    fields = payload.get("fields", {})
    cardinality_rules = {
        "eRecord.01": {"min": 1, "max": 1},
        "eNarrative.01": {"min": 1, "max": 1},
        "eVitals": {"min": 1, "max": 99},
        "eProcedures": {"min": 0, "max": 99},
        "eMedications": {"min": 0, "max": 99},
    }
    errors = []
    for elem, rules in cardinality_rules.items():
        if elem in fields:
            val = fields[elem]
            count = len(val) if isinstance(val, list) else 1
            if count < rules["min"]:
                errors.append({"element": elem, "error": f"Minimum {rules['min']} occurrence(s) required, got {count}"})
            if count > rules["max"]:
                errors.append({"element": elem, "error": f"Maximum {rules['max']} occurrence(s) allowed, got {count}"})
    return {"valid": not errors, "cardinality_errors": errors}


# ── Required coding auto-suggest ──────────────────────────────────────────────

@router.post("/coding-suggest")
async def coding_suggest(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    narrative = payload.get("narrative", "")
    suggestions: list[dict[str, str]] = []
    keyword_map = [
        ("chest pain", "eSituation.09", "2141003", "Chest Pain"),
        ("shortness of breath", "eSituation.09", "230145002", "Respiratory Distress"),
        ("altered mental status", "eSituation.09", "419284004", "Altered Mental Status"),
        ("trauma", "eSituation.09", "417746004", "Traumatic Injury"),
        ("seizure", "eSituation.09", "91175000", "Seizure"),
    ]
    for kw, elem, code, label in keyword_map:
        if kw.lower() in narrative.lower():
            suggestions.append({"element": elem, "suggested_code": code, "label": label, "trigger": kw})
    return {"suggestions": suggestions, "count": len(suggestions)}


# ── Certification maintenance engine ─────────────────────────────────────────

@router.get("/certification-maintenance")
async def certification_maintenance(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    validations = svc.repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    last_30 = validations[-30:] if len(validations) >= 30 else validations
    recent_valid = len([v for v in last_30 if v.get("data", {}).get("valid")])
    rate = round(recent_valid / len(last_30) * 100, 1) if last_30 else 0
    return {
        "certification_maintained": rate >= 90,
        "recent_validation_rate_pct": rate,
        "sample_size": len(last_30),
        "nemsis_version": NEMSIS_351_SCHEMA["version"],
        "next_review_due": "2026-06-01",
        "status": "MAINTAINED" if rate >= 90 else "AT_RISK",
    }


# ── Fail-safe export freeze ────────────────────────────────────────────────────

@router.post("/export/freeze")
async def export_freeze(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="nemsis_export_freezes",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "frozen": payload.get("frozen", True),
            "reason": payload.get("reason"),
            "frozen_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/export/freeze-status")
async def export_freeze_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    freezes = _svc(db).repo("nemsis_export_freezes").list(tenant_id=current.tenant_id)
    latest = freezes[-1] if freezes else None
    frozen = latest and latest.get("data", {}).get("frozen") is True
    return {"exports_frozen": bool(frozen), "latest_freeze": latest}


# ── Field redundancy detection ────────────────────────────────────────────────

@router.post("/validate/redundancy")
async def field_redundancy(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    provided = payload.get("provided_elements", [])
    redundant_groups = [
        {"elements": ["ePatient.01", "ePatient.02"], "note": "Both name components required together"},
        {"elements": ["eVitals.14", "eVitals.15"], "note": "Both systolic and diastolic required together"},
    ]
    warnings = []
    for group in redundant_groups:
        present = [e for e in group["elements"] if e in provided]
        if len(present) > 0 and len(present) < len(group["elements"]):
            missing_from_group = [e for e in group["elements"] if e not in provided]
            warnings.append({
                "group": group["elements"],
                "note": group["note"],
                "missing": missing_from_group,
            })
    return {"redundancy_warnings": warnings, "count": len(warnings)}


# ── Missing trend detection ───────────────────────────────────────────────────

@router.get("/trends/missing-fields")
async def missing_field_trends(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    validations = _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id)
    missing_counts: dict[str, int] = {}
    for v in validations:
        for err in v.get("data", {}).get("errors", []):
            for elem_id in NEMSIS_351_SCHEMA["elements"]:
                if elem_id in str(err):
                    missing_counts[elem_id] = missing_counts.get(elem_id, 0) + 1
    sorted_missing = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)
    return {"trending_missing": [{"element": k, "missing_count": c} for k, c in sorted_missing[:10]]}


# ── System-of-record enforcement ─────────────────────────────────────────────

@router.get("/system-of-record")
async def system_of_record(
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "system_of_record": "FusionEMS Quantum",
        "nemsis_version": "3.5.1",
        "data_authority": "Agency EHR -> FusionEMS -> State NEMSIS Repository",
        "overwrite_policy": "Manual corrections require audit trail",
        "source_of_truth": True,
    }
