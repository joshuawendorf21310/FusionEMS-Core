from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.epcr.ai_smart_text import SmartTextEngine
from core_app.epcr.chart_model import Chart, ChartStatus
from core_app.epcr.completeness_engine import CompletenessEngine
from core_app.epcr.evidence_service import EvidenceService
from core_app.epcr.jcs_hash import build_chart_hash_payload, jcs_sha256
from core_app.epcr.nemsis_exporter import NEMSISExporter
from core_app.epcr.sync_engine import SyncConflictPolicy, SyncEngine
from core_app.nemsis.validator import NEMSISValidator
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/epcr", tags=["ePCR"])


def require_role(*roles: str):
    def dep(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current

    return dep


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


@router.post("/charts")
async def create_chart(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    chart_mode = payload.get("chart_mode", "bls")
    resource_pack_id = payload.get("resource_pack_id")
    chart_id = str(uuid.uuid4())
    chart = Chart(
        chart_id=chart_id,
        tenant_id=str(current.tenant_id),
        chart_mode=chart_mode,
        resource_pack_id=resource_pack_id,
        created_by=str(current.user_id),
        last_modified_by=str(current.user_id),
    )
    chart_dict = chart.to_dict()
    score_result = CompletenessEngine().score_chart(chart_dict, chart_mode)
    chart.completeness_score = score_result["score"]
    chart.completeness_issues = [m["label"] for m in score_result["missing"]]
    chart_dict = chart.to_dict()
    rec = await _svc(db).create(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=chart_dict,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return rec


@router.get("/charts")
async def list_charts(
    status: str | None = None,
    mode: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    from sqlalchemy import text

    clauses = ["tenant_id = :tenant_id", "deleted_at IS NULL"]
    params: dict[str, Any] = {"tenant_id": str(current.tenant_id), "limit": limit, "offset": offset}
    if status:
        clauses.append("data->>'chart_status' = :status")
        params["status"] = status
    if mode:
        clauses.append("data->>'chart_mode' = :mode")
        params["mode"] = mode
    sql = text(
        "SELECT * FROM epcr_charts "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY created_at DESC "
        "LIMIT :limit OFFSET :offset"
    )
    rows = db.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/charts/{chart_id}")
async def get_chart(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return rec


@router.patch("/charts/{chart_id}")
async def update_chart(
    chart_id: str,
    patch: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    updated_data = {**rec["data"], **patch}
    updated_data["last_modified_by"] = str(current.user_id)
    updated_data["updated_at"] = datetime.now(UTC).isoformat()
    mode = updated_data.get("chart_mode", "bls")
    score_result = CompletenessEngine().score_chart(updated_data, mode)
    updated_data["completeness_score"] = score_result["score"]
    updated_data["completeness_issues"] = [m["label"] for m in score_result["missing"]]
    svc = _svc(db)
    updated_rec = await svc.update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=getattr(request.state, "correlation_id", None),
        commit=False,
    )
    if updated_rec is None:
        raise HTTPException(status_code=409, detail="Version conflict")
    event_entry = SyncEngine().create_event_log_entry(
        chart_id=chart_id,
        action="chart_updated",
        actor=str(current.user_id),
        field_changes={"fields": list(patch.keys())},
    )
    await svc.create(
        table="epcr_event_log",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**event_entry, "chart_id": chart_id},
        correlation_id=getattr(request.state, "correlation_id", None),
        commit=False,
    )
    db.commit()
    return updated_rec


@router.delete("/charts/{chart_id}")
async def cancel_chart(
    chart_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    updated_data = {**rec["data"], "chart_status": ChartStatus.CANCELLED.value}
    await _svc(db).update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data, "status": ChartStatus.CANCELLED.value},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"cancelled": True, "chart_id": chart_id}


@router.post("/charts/{chart_id}/vitals")
async def add_vital(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    if "vital_id" not in payload:
        payload["vital_id"] = str(uuid.uuid4())
    updated_data = dict(rec["data"])
    updated_data.setdefault("vitals", []).append(payload)
    updated_data["updated_at"] = datetime.now(UTC).isoformat()
    updated_rec = await _svc(db).update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if updated_rec is None:
        raise HTTPException(status_code=409, detail="Version conflict")
    return updated_rec


@router.post("/charts/{chart_id}/medications")
async def add_medication(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    if "med_id" not in payload:
        payload["med_id"] = str(uuid.uuid4())
    updated_data = dict(rec["data"])
    updated_data.setdefault("medications", []).append(payload)
    updated_data["updated_at"] = datetime.now(UTC).isoformat()
    updated_rec = await _svc(db).update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if updated_rec is None:
        raise HTTPException(status_code=409, detail="Version conflict")
    return updated_rec


@router.post("/charts/{chart_id}/procedures")
async def add_procedure(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    if "proc_id" not in payload:
        payload["proc_id"] = str(uuid.uuid4())
    updated_data = dict(rec["data"])
    updated_data.setdefault("procedures", []).append(payload)
    updated_data["updated_at"] = datetime.now(UTC).isoformat()
    updated_rec = await _svc(db).update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if updated_rec is None:
        raise HTTPException(status_code=409, detail="Version conflict")
    return updated_rec


@router.post("/charts/{chart_id}/assessments")
async def add_assessment(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    if "assessment_id" not in payload:
        payload["assessment_id"] = str(uuid.uuid4())
    updated_data = dict(rec["data"])
    updated_data.setdefault("assessments", []).append(payload)
    updated_data["updated_at"] = datetime.now(UTC).isoformat()
    updated_rec = await _svc(db).update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if updated_rec is None:
        raise HTTPException(status_code=409, detail="Version conflict")
    return updated_rec


@router.post("/charts/{chart_id}/attachments")
async def upload_attachment(
    chart_id: str,
    request: Request,
    file: UploadFile = File(...),
    attachment_type: str = Form("general"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    content = await file.read()
    attachment_record = EvidenceService(get_settings().s3_bucket_docs).store_attachment(
        chart_id=chart_id,
        attachment_type=attachment_type,
        content=content,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        tenant_id=str(current.tenant_id),
    )
    updated_data = dict(rec["data"])
    updated_data.setdefault("attachments", []).append(attachment_record)
    updated_data["updated_at"] = datetime.now(UTC).isoformat()
    await _svc(db).update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return attachment_record


@router.get("/charts/{chart_id}/attachments/{attachment_id}/url")
async def get_attachment_url(
    chart_id: str,
    attachment_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    attachments = rec.get("data", {}).get("attachments", [])
    attachment = next((a for a in attachments if a.get("attachment_id") == attachment_id), None)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    url = EvidenceService(get_settings().s3_bucket_docs).get_presigned_url(attachment["s3_key"])
    return {"attachment_id": attachment_id, "url": url}


@router.post("/charts/{chart_id}/sync")
async def sync_chart(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    local_chart = payload.get("local_chart", {})
    payload.get("device_id", "")
    conflict_policy_str = payload.get("conflict_policy", "last_write_wins")
    try:
        policy = SyncConflictPolicy(conflict_policy_str)
    except ValueError:
        policy = SyncConflictPolicy.LAST_WRITE_WINS
    server_chart_data = rec.get("data", {})
    resolved, conflict_notes = SyncEngine().resolve_conflict(local_chart, server_chart_data, policy)
    resolved["updated_at"] = datetime.now(UTC).isoformat()
    await _svc(db).update(
        table="epcr_charts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": resolved},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {
        "resolved_chart": resolved,
        "conflict_notes": conflict_notes,
        "sync_status": resolved.get("sync_status", "synced"),
    }


@router.post("/charts/{chart_id}/export/nemsis")
async def export_nemsis(
    chart_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_data = rec.get("data", {})
    xml_bytes = NEMSISExporter().export_chart(chart_data, agency_info={})
    result = NEMSISValidator().validate_xml_bytes(xml_bytes)
    xml_b64 = base64.b64encode(xml_bytes).decode()
    job_id = str(uuid.uuid4())
    await _svc(db).create(
        table="nemsis_export_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "job_id": job_id,
            "chart_id": chart_id,
            "valid": result.valid,
            "export_errors": [i.plain_message for i in result.issues if i.severity == "error"],
            "exported_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {
        "job_id": job_id,
        "xml_b64": xml_b64,
        "valid": result.valid,
        "export_errors": [i.plain_message for i in result.issues],
    }


@router.get("/charts/{chart_id}/completeness")
async def chart_completeness(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_data = rec.get("data", {})
    mode = chart_data.get("chart_mode", "bls")
    return CompletenessEngine().score_chart(chart_data, mode)


@router.post("/charts/{chart_id}/ai/narrative")
async def ai_narrative(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    tone = payload.get("tone", "clinical")
    chart_data = rec.get("data", {})
    result = SmartTextEngine().generate_narrative(chart_data, tone)
    await _svc(db).create(
        table="epcr_ai_outputs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"chart_id": chart_id, "output_type": "narrative", **result},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


@router.post("/charts/{chart_id}/ai/handoff")
async def ai_handoff(
    chart_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_data = rec.get("data", {})
    result = SmartTextEngine().generate_handoff_summary(chart_data)
    await _svc(db).create(
        table="epcr_ai_outputs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"chart_id": chart_id, "output_type": "handoff", **result},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


@router.get("/charts/{chart_id}/ai/missing-docs")
async def ai_missing_docs(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_data = rec.get("data", {})
    mode = chart_data.get("chart_mode", "bls")
    return SmartTextEngine().detect_missing_documentation(chart_data, mode)


@router.get("/charts/{chart_id}/ai/contradictions")
async def ai_contradictions(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_data = rec.get("data", {})
    return SmartTextEngine().detect_contradictions(chart_data)


@router.post("/charts/{chart_id}/submit")
async def submit_chart(
    chart_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")

    chart_data = rec.get("data", {})

    # --- Guard 1: completeness ---
    readiness = CompletenessEngine().score_for_submission(chart_data)
    if not readiness["ready"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Chart not ready for submission",
                "blocking_issues": readiness["blocking_issues"],
            },
        )

    # --- Guard 2: NEMSIS validation ---
    xml_bytes = NEMSISExporter().export_chart(chart_data, agency_info={})
    val_result = NEMSISValidator().validate_xml_bytes(xml_bytes)
    error_issues = [i.plain_message for i in val_result.issues if i.severity == "error"]
    if error_issues:
        raise HTTPException(
            status_code=422,
            detail={"message": "NEMSIS validation failed", "issues": error_issues},
        )

    # --- Guard 3: idempotency — already submitted ---
    if chart_data.get("chart_status") == ChartStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=409,
            detail={"message": "Chart already submitted", "chart_id": chart_id},
        )

    submitted_at = datetime.now(UTC)
    submitted_at_iso = submitted_at.isoformat()

    # --- Deterministic SHA-256 (JCS / RFC 8785) ---
    hash_payload = build_chart_hash_payload(chart_data)
    hash_payload["submitted_at"] = submitted_at_iso
    sha256_hex = jcs_sha256(hash_payload)

    updated_data = {
        **chart_data,
        "chart_status": ChartStatus.SUBMITTED.value,
        "updated_at": submitted_at_iso,
        "submitted_at": submitted_at_iso,
        "sha256_submitted": sha256_hex,
    }

    corr_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)

    try:
        updated_rec = await svc.update(
            table="epcr_charts",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            record_id=uuid.UUID(str(rec["id"])),
            expected_version=rec["version"],
            patch={
                "data": updated_data,
                "status": ChartStatus.SUBMITTED.value,
                "submitted_at": submitted_at,
                "sha256_submitted": sha256_hex,
            },
            correlation_id=corr_id,
            commit=False,
        )
        if updated_rec is None:
            raise HTTPException(status_code=409, detail="Version conflict — retry")

        event_entry = SyncEngine().create_event_log_entry(
            chart_id=chart_id,
            action="chart_submitted",
            actor=str(current.user_id),
            field_changes={"submitted_at": submitted_at_iso, "sha256_submitted": sha256_hex},
        )
        await svc.create(
            table="epcr_event_log",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={**event_entry, "chart_id": chart_id, "sha256_submitted": sha256_hex},
            correlation_id=corr_id,
            commit=False,
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Submit transaction failed: {exc}") from exc

    # --- Post-commit: publish realtime event ---
    try:
        publisher = get_event_publisher()
        await publisher.publish(
            event_name="epcr.chart.submitted",
            tenant_id=current.tenant_id,
            entity_id=uuid.UUID(str(rec["id"])),
            payload={
                "chart_id": chart_id,
                "status": ChartStatus.SUBMITTED.value,
                "submitted_at": submitted_at_iso,
                "sha256_submitted": sha256_hex,
            },
            entity_type="epcr_charts",
            correlation_id=corr_id,
        )
    except Exception:
        pass

    return {
        "submitted": True,
        "chart_id": chart_id,
        "submitted_at": submitted_at_iso,
        "sha256_submitted": sha256_hex,
    }


@router.get("/charts/{chart_id}/event-log")
async def get_event_log(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return (
        _svc(db)
        .repo("epcr_event_log")
        .list_raw_by_field(
            "chart_id",
            chart_id,
            tenant_id=current.tenant_id,
            limit=200,
        )
    )
