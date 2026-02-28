from __future__ import annotations

import base64
import hashlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from core_app.ai.service import AiService
from core_app.api.dependencies import db_session_dependency, require_role
from core_app.compliance.nemsis_xml_generator import build_nemsis_document
from core_app.nemsis.cs_scenario_parser import CandSParser
from core_app.nemsis.pack_manager import PackManager
from core_app.nemsis.validator import NEMSISValidator
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/nemsis/studio", tags=["NEMSIS Compliance Studio"])

_WRITE = require_role("founder", "agency_admin")

_AI_SYSTEM = (
    "You are a NEMSIS 3.5.x compliance expert and EMS data engineer. "
    "You help non-engineers understand and fix NEMSIS validation errors. "
    "Respond only with valid JSON."
)

_AI_USER_TEMPLATE = (
    "A Wisconsin NEMSIS validation produced this issue:\n"
    "- Element: {element_id}\n"
    "- Section: {ui_section}\n"
    "- Severity: {severity}\n"
    "- Stage: {stage} ({rule_source})\n"
    "- Message: {plain_message}\n"
    "- Technical detail: {technical_message}\n"
    "- Fix hint: {fix_hint}\n\n"
    "Respond with JSON:\n"
    "{{\n"
    '  "plain_explanation": "2-3 sentences in plain English for a non-engineer",\n'
    '  "fix_type": "one of: exporter_bug|mapping_bug|ui_rule|code_list|facility_resolver|datetime_format|missing_element|structural",\n'
    '  "patch_task": {{\n'
    '    "task_id": "<generate a short slug>",\n'
    '    "title": "<short title>",\n'
    '    "description": "<what needs to change>",\n'
    '    "affected_file_hint": "<which file/layer likely needs changing>",\n'
    '    "element_id": "{element_id}",\n'
    '    "fix_type": "<same as above>",\n'
    '    "steps": ["step 1", "step 2", "step 3"]\n'
    "  }},\n"
    '  "confidence": 0.0\n'
    "}}"
)

_SAFE_AI_DEFAULT = {
    "plain_explanation": "Unable to generate explanation at this time.",
    "fix_type": "structural",
    "patch_task": {
        "task_id": "unknown",
        "title": "Review validation issue",
        "description": "Manual review required.",
        "affected_file_hint": "Unknown",
        "element_id": "",
        "fix_type": "structural",
        "steps": ["Review the validation issue manually."],
    },
    "confidence": 0.0,
}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _manager(db: Session, current: CurrentUser) -> PackManager:
    return PackManager(db, get_event_publisher(), current.tenant_id, current.user_id)


def _cache_key(validation_result_id: str, issue_index: int) -> str:
    raw = f"{validation_result_id}:{issue_index}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/validate-file")
async def validate_file(
    request: Request,
    file: UploadFile = File(...),
    state_code: str = Query(default="WI"),
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    xml_bytes = await file.read()
    validator = NEMSISValidator()
    result = validator.validate_xml_bytes(xml_bytes, state_code=state_code)
    correlation_id = getattr(request.state, "correlation_id", None)
    rec = await _svc(db).create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "valid": result.valid,
            "issues": [i.to_dict() for i in result.issues],
            "stage_results": result.stage_results,
            "validated_at": result.validated_at,
            "state_code": state_code,
            "source_filename": file.filename,
        },
        correlation_id=correlation_id,
    )
    return {**result.to_dict(), "record_id": str(rec["id"])}


@router.post("/validate-bytes")
async def validate_bytes(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    xml_b64 = payload.get("xml_b64", "")
    state_code = payload.get("state_code", "WI")
    try:
        xml_bytes = base64.b64decode(xml_b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {exc}") from exc

    validator = NEMSISValidator()
    result = validator.validate_xml_bytes(xml_bytes, state_code=state_code)
    correlation_id = getattr(request.state, "correlation_id", None)
    rec = await _svc(db).create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "valid": result.valid,
            "issues": [i.to_dict() for i in result.issues],
            "stage_results": result.stage_results,
            "validated_at": result.validated_at,
            "state_code": state_code,
            "source_filename": None,
        },
        correlation_id=correlation_id,
    )
    return {**result.to_dict(), "record_id": str(rec["id"])}


@router.get("/validation-results")
async def list_validation_results(
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id, limit=50)


@router.get("/validation-results/{result_id}")
async def get_validation_result(
    result_id: str,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("nemsis_validation_results").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(result_id)
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Validation result not found")
    return rec


@router.post("/ai-explain")
async def ai_explain(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    validation_result_id = payload["validation_result_id"]
    issue_index = int(payload["issue_index"])

    cache_key = _cache_key(validation_result_id, issue_index)
    existing_rows = _svc(db).repo("nemsis_ai_explanations").list_raw_by_field(
        "cache_key", cache_key, limit=1
    )
    if existing_rows:
        return existing_rows[0]

    vr = _svc(db).repo("nemsis_validation_results").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(validation_result_id)
    )
    if vr is None:
        raise HTTPException(status_code=404, detail="Validation result not found")

    issues = vr.get("data", {}).get("issues", [])
    if issue_index >= len(issues):
        raise HTTPException(status_code=400, detail="issue_index out of range")

    issue = issues[issue_index]
    user_prompt = _AI_USER_TEMPLATE.format(
        element_id=issue.get("element_id", ""),
        ui_section=issue.get("ui_section", ""),
        severity=issue.get("severity", ""),
        stage=issue.get("stage", ""),
        rule_source=issue.get("rule_source", ""),
        plain_message=issue.get("plain_message", ""),
        technical_message=issue.get("technical_message", ""),
        fix_hint=issue.get("fix_hint", ""),
    )

    try:
        ai = AiService()
        raw_response, meta = ai.chat(system=_AI_SYSTEM, user=user_prompt)
        explanation = json.loads(raw_response)
    except Exception:
        explanation = dict(_SAFE_AI_DEFAULT)

    explanation["element_id"] = issue.get("element_id", "")
    explanation.setdefault("patch_task", {})["element_id"] = issue.get("element_id", "")

    correlation_id = getattr(request.state, "correlation_id", None)
    rec = await _svc(db).create(
        table="nemsis_ai_explanations",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "validation_result_id": validation_result_id,
            "issue_index": issue_index,
            "cache_key": cache_key,
            "explanation": explanation,
            "element_id": issue.get("element_id", ""),
        },
        correlation_id=correlation_id,
    )
    return rec


@router.post("/ai-explain-batch")
async def ai_explain_batch(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    validation_result_id = payload["validation_result_id"]
    vr = _svc(db).repo("nemsis_validation_results").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(validation_result_id)
    )
    if vr is None:
        raise HTTPException(status_code=404, detail="Validation result not found")

    issues = vr.get("data", {}).get("issues", [])[:20]
    results = []
    correlation_id = getattr(request.state, "correlation_id", None)

    for idx, issue in enumerate(issues):
        cache_key = _cache_key(validation_result_id, idx)
        existing = _svc(db).repo("nemsis_ai_explanations").list_raw_by_field(
            "cache_key", cache_key, limit=1
        )
        if existing:
            results.append(existing[0])
            continue

        user_prompt = _AI_USER_TEMPLATE.format(
            element_id=issue.get("element_id", ""),
            ui_section=issue.get("ui_section", ""),
            severity=issue.get("severity", ""),
            stage=issue.get("stage", ""),
            rule_source=issue.get("rule_source", ""),
            plain_message=issue.get("plain_message", ""),
            technical_message=issue.get("technical_message", ""),
            fix_hint=issue.get("fix_hint", ""),
        )
        try:
            ai = AiService()
            raw_response, _meta = ai.chat(system=_AI_SYSTEM, user=user_prompt)
            explanation = json.loads(raw_response)
        except Exception:
            explanation = dict(_SAFE_AI_DEFAULT)

        explanation["element_id"] = issue.get("element_id", "")

        rec = await _svc(db).create(
            table="nemsis_ai_explanations",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "validation_result_id": validation_result_id,
                "issue_index": idx,
                "cache_key": cache_key,
                "explanation": explanation,
                "element_id": issue.get("element_id", ""),
            },
            correlation_id=correlation_id,
        )
        results.append(rec)

    return {"count": len(results), "explanations": results}


@router.post("/scenarios/upload")
async def upload_scenarios(
    request: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    content = await file.read()
    parser = CandSParser()
    filename = file.filename or "upload"

    if filename.lower().endswith(".zip"):
        scenarios = parser.parse_zip_bundle(content)
    else:
        scenario = parser.detect_and_parse(filename, content)
        scenarios = [scenario] if scenario is not None else []

    correlation_id = getattr(request.state, "correlation_id", None)
    stored = []
    for scenario in scenarios:
        rec = await _svc(db).create(
            table="nemsis_cs_scenarios",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "summary": scenario.summary,
                "dataset_type": scenario.dataset_type,
                "expected_result": scenario.expected_result,
                "sections_involved": [
                    {"name": s.name, "element_count": s.element_count}
                    for s in scenario.sections_involved
                ],
                "raw_data": scenario.raw_data,
                "nemsis_version": scenario.nemsis_version,
                "state_code": scenario.state_code,
                "test_type": scenario.test_type,
            },
            correlation_id=correlation_id,
        )
        stored.append(rec)

    return {"count": len(stored), "scenarios": stored}


@router.get("/scenarios")
async def list_scenarios(
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_cs_scenarios").list(tenant_id=current.tenant_id)


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: str,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("nemsis_cs_scenarios").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(scenario_id)
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return rec


@router.post("/scenarios/{scenario_id}/run")
async def run_scenario(
    scenario_id: str,
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("nemsis_cs_scenarios").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(scenario_id)
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    raw_data = rec.get("data", {}).get("raw_data", {})
    xml_content = raw_data.get("xml") or raw_data.get("xmlContent") or raw_data.get("xml_content")
    if not xml_content:
        raise HTTPException(status_code=422, detail="Scenario does not contain embedded XML for validation")

    xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
    state_code = rec.get("data", {}).get("state_code", "WI")

    validator = NEMSISValidator()
    result = validator.validate_xml_bytes(xml_bytes, state_code=state_code)

    correlation_id = getattr(request.state, "correlation_id", None)
    stored = await _svc(db).create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "valid": result.valid,
            "issues": [i.to_dict() for i in result.issues],
            "stage_results": result.stage_results,
            "validated_at": result.validated_at,
            "state_code": state_code,
            "source": f"scenario:{scenario_id}",
        },
        correlation_id=correlation_id,
    )
    return {**result.to_dict(), "record_id": str(stored["id"])}


@router.post("/scenarios/{scenario_id}/export-and-validate")
async def export_and_validate(
    scenario_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    incident_id = payload.get("incident_id")
    if not incident_id:
        raise HTTPException(status_code=400, detail="incident_id required")

    incident_rec = _svc(db).repo("nemsis_export_jobs").list_raw_by_field("incident_id", incident_id, limit=1)
    incident = incident_rec[0].get("data", {}) if incident_rec else {"id": incident_id}

    try:
        xml_bytes = build_nemsis_document(
            incident=incident,
            patient=incident.get("patient", {}),
            vitals=incident.get("vitals", []),
            agency_info=incident.get("agency", {}),
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"XML generation failed: {exc}") from exc

    scenario_rec = _svc(db).repo("nemsis_cs_scenarios").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(scenario_id)
    )
    state_code = (scenario_rec or {}).get("data", {}).get("state_code", "WI") if scenario_rec else "WI"

    validator = NEMSISValidator()
    result = validator.validate_xml_bytes(xml_bytes, state_code=state_code)

    correlation_id = getattr(request.state, "correlation_id", None)
    stored = await _svc(db).create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "valid": result.valid,
            "issues": [i.to_dict() for i in result.issues],
            "stage_results": result.stage_results,
            "validated_at": result.validated_at,
            "state_code": state_code,
            "source": f"export_validate:incident={incident_id}:scenario={scenario_id}",
        },
        correlation_id=correlation_id,
    )
    return {**result.to_dict(), "record_id": str(stored["id"])}


@router.get("/diff/packs")
async def diff_packs(
    from_pack_id: str = Query(...),
    to_pack_id: str = Query(...),
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    manager = _manager(db, current)

    from_pack = manager.get_pack(from_pack_id)
    to_pack = manager.get_pack(to_pack_id)
    if from_pack is None:
        raise HTTPException(status_code=404, detail="from_pack_id not found")
    if to_pack is None:
        raise HTTPException(status_code=404, detail="to_pack_id not found")

    from_manifest: dict[str, str] = from_pack.get("data", {}).get("sha256_manifest", {})
    to_manifest: dict[str, str] = to_pack.get("data", {}).get("sha256_manifest", {})

    from_files = set(from_manifest.keys())
    to_files = set(to_manifest.keys())

    added = list(to_files - from_files)
    removed = list(from_files - to_files)
    changed = [
        f for f in from_files & to_files
        if from_manifest[f] != to_manifest[f]
    ]
    unchanged = [
        f for f in from_files & to_files
        if from_manifest[f] == to_manifest[f]
    ]

    return {
        "from_pack": {"id": from_pack_id, "data": from_pack.get("data", {})},
        "to_pack": {"id": to_pack_id, "data": to_pack.get("data", {})},
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "unchanged_count": len(unchanged),
        },
    }


@router.get("/certification-checklist")
async def certification_checklist(
    state_code: str = Query(default="WI"),
    pack_type: str = Query(default="bundle"),
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    manager = _manager(db, current)
    active_pack = manager.get_active_pack(state_code, pack_type)

    pack_complete = False
    if active_pack:
        completeness = manager.get_pack_completeness(str(active_pack["id"]))
        pack_complete = completeness.get("complete", False)

    validations = _svc(db).repo("nemsis_validation_results").list(tenant_id=current.tenant_id, limit=100)
    total = len(validations)
    passed = sum(1 for v in validations if v.get("data", {}).get("valid") is True)
    validation_rate = round(passed / total * 100, 1) if total > 0 else 0.0

    scenarios = _svc(db).repo("nemsis_cs_scenarios").list(tenant_id=current.tenant_id, limit=100)
    has_pass_scenario = any(
        s.get("data", {}).get("expected_result") == "PASS" for s in scenarios
    )

    last_validation_at = None
    if validations:
        last_validation_at = validations[0].get("created_at")
        if hasattr(last_validation_at, "isoformat"):
            last_validation_at = last_validation_at.isoformat()

    recommendations = []
    if not pack_complete:
        recommendations.append("Upload all required resource pack files and activate the pack.")
    if validation_rate < 95.0:
        recommendations.append("Improve data quality to reach ≥95% validation pass rate.")
    if not has_pass_scenario:
        recommendations.append("Upload at least one C&S scenario with expected result PASS.")
    if last_validation_at is None:
        recommendations.append("Run at least one NEMSIS XML validation.")

    return {
        "resource_pack_complete": pack_complete,
        "active_pack_id": str(active_pack["id"]) if active_pack else None,
        "validation_rate_percent": validation_rate,
        "total_validations": total,
        "passed_validations": passed,
        "has_pass_scenario": has_pass_scenario,
        "last_validation_at": last_validation_at,
        "recommendations": recommendations,
        "certified": pack_complete and validation_rate >= 95.0 and has_pass_scenario,
    }


@router.post("/patch-tasks")
async def create_patch_task(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    correlation_id = getattr(request.state, "correlation_id", None)
    return await _svc(db).create(
        table="nemsis_patch_tasks",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "task_id": payload.get("task_id") or str(uuid.uuid4()),
            "title": payload.get("title", ""),
            "description": payload.get("description", ""),
            "affected_file_hint": payload.get("affected_file_hint", ""),
            "element_id": payload.get("element_id", ""),
            "fix_type": payload.get("fix_type", "structural"),
            "steps": payload.get("steps", []),
            "status": "pending",
        },
        correlation_id=correlation_id,
    )


@router.get("/patch-tasks")
async def list_patch_tasks(
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("nemsis_patch_tasks").list(tenant_id=current.tenant_id)


@router.patch("/patch-tasks/{task_id}")
async def update_patch_task_status(
    task_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    allowed_statuses = {"pending", "in_progress", "completed", "rejected"}
    new_status = payload.get("status")
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(allowed_statuses)}")

    rec = _svc(db).repo("nemsis_patch_tasks").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(task_id)
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Patch task not found")

    correlation_id = getattr(request.state, "correlation_id", None)
    result = await _svc(db).update(
        table="nemsis_patch_tasks",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(task_id),
        expected_version=int(rec.get("version", 1)),
        patch={"status": new_status},
        correlation_id=correlation_id,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict")
    return result


@router.post("/patch-tasks/generate-from-result")
async def generate_patch_tasks_from_result(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(_WRITE),
    db: Session = Depends(db_session_dependency),
):
    validation_result_id = payload.get("validation_result_id")
    if not validation_result_id:
        raise HTTPException(status_code=400, detail="validation_result_id required")

    vr = _svc(db).repo("nemsis_validation_results").get(
        tenant_id=current.tenant_id, record_id=uuid.UUID(str(validation_result_id))
    )
    if vr is None:
        raise HTTPException(status_code=404, detail="Validation result not found")

    issues = vr.get("data", {}).get("issues", [])
    errors = [i for i in issues if i.get("severity") == "error"]
    correlation_id = getattr(request.state, "correlation_id", None)
    created_ids = []
    for issue in errors:
        element_id = issue.get("element_id", "")
        rec = await _svc(db).create(
            table="nemsis_patch_tasks",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "task_id": str(uuid.uuid4()),
                "title": f"Fix {element_id}: {issue.get('plain_message', issue.get('technical_message', '')[:80])}",
                "description": issue.get("technical_message", issue.get("plain_message", "")),
                "affected_file_hint": issue.get("ui_section", ""),
                "element_id": element_id,
                "fix_type": "structural" if issue.get("severity") == "error" else "data",
                "steps": [issue.get("fix_hint", "Review the failing element and correct the value.")] if issue.get("fix_hint") else [],
                "status": "pending",
                "source_validation_result_id": str(validation_result_id),
            },
            correlation_id=correlation_id,
        )
        created_ids.append(str(rec["id"]))

    return {
        "generated": len(created_ids),
        "task_ids": created_ids,
        "source_validation_result_id": str(validation_result_id),
    }
