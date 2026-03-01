"""NEMSIS state submission results router.

Endpoints:
  POST /api/v1/epcr/charts/{chart_id}/nemsis-submissions
      Initiates a new state submission for a submitted chart.
      Exports XML → stores to S3 → records nemsis_submission_results row
      → appends initial status-history entry.

  GET  /api/v1/epcr/charts/{chart_id}/nemsis-submissions
      Lists all submission attempts for a chart.

  GET  /api/v1/epcr/nemsis-submissions/{submission_id}
      Returns a single submission record with full status history.

  POST /api/v1/epcr/nemsis-submissions/{submission_id}/acknowledge
      Records state acknowledgement (999/277CA response), stores ACK to S3,
      advances status → 'acknowledged', appends history.

  POST /api/v1/epcr/nemsis-submissions/{submission_id}/accept
      Records accepted outcome, stores response to S3,
      advances status → 'accepted', locks chart (status='locked').

  POST /api/v1/epcr/nemsis-submissions/{submission_id}/reject
      Records rejection, stores response to S3, advances → 'rejected'.

  POST /api/v1/epcr/nemsis-submissions/{submission_id}/retry
      Creates a new submission attempt linked to the same chart.
      Increments attempt_count. Previous attempt remains in history.

Status machine:
  pending → submitted → acknowledged → accepted | rejected
                      ↘ rejected (direct, no ACK)
  rejected → (new retry creates fresh row)
"""

from __future__ import annotations

import base64 as _b64
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.epcr.chart_model import ChartStatus
from core_app.epcr.jcs_hash import jcs_sha256
from core_app.epcr.nemsis_exporter import NEMSISExporter
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/epcr", tags=["ePCR NEMSIS Submissions"])

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"submitted"},
    "submitted": {"acknowledged", "rejected"},
    "acknowledged": {"accepted", "rejected"},
    "accepted": set(),
    "rejected": set(),
}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _s3_client():
    return boto3.client("s3")


def _exports_bucket() -> str:
    return get_settings().s3_bucket_exports


def _upload_to_s3(content: bytes, key: str, content_type: str) -> tuple[str, str]:
    bucket = _exports_bucket()
    _s3_client().put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
    return bucket, key


# --------------------------------------------------------------------------- #
# POST /charts/{chart_id}/nemsis-submissions — initiate submission             #
# --------------------------------------------------------------------------- #
@router.post("/charts/{chart_id}/nemsis-submissions")
async def create_submission(
    chart_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)

    chart_rec = svc.repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if chart_rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")

    chart_data = chart_rec.get("data", {})
    if chart_data.get("chart_status") not in (
        ChartStatus.SUBMITTED.value,
        ChartStatus.LOCKED.value,
    ):
        raise HTTPException(
            status_code=422,
            detail="Chart must be in 'submitted' or 'locked' status before submitting to a state endpoint",
        )

    state_code: str = payload.get("state_code", "")
    endpoint_url: str | None = payload.get("endpoint_url")
    if not state_code:
        raise HTTPException(status_code=422, detail="state_code is required")

    # Export XML
    xml_bytes = NEMSISExporter().export_chart(
        chart_data, agency_info=payload.get("agency_info", {})
    )

    sha256_hex = jcs_sha256({"xml_bytes_b64": xml_bytes.hex(), "chart_id": chart_id})

    submission_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Store XML to S3
    xml_s3_key = f"nemsis-submissions/{current.tenant_id}/{chart_id}/{submission_id}/payload.xml"
    try:
        xml_s3_bucket, xml_s3_key = _upload_to_s3(xml_bytes, xml_s3_key, "application/xml")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"S3 upload failed: {exc}") from exc

    sub_data: dict[str, Any] = {
        "submission_id": submission_id,
        "chart_id": chart_id,
        "state_code": state_code,
        "endpoint_url": endpoint_url,
        "status": "pending",
        "xml_s3_bucket": xml_s3_bucket,
        "xml_s3_key": xml_s3_key,
        "sha256_payload": sha256_hex,
        "attempt_count": 1,
        "created_at": now,
        "updated_at": now,
    }

    sub_rec = await svc.create(
        table="nemsis_submission_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=sub_data,
        typed_columns={"chart_id": chart_id, "state_code": state_code, "status": "pending"},
        correlation_id=corr,
    )

    await svc.create(
        table="nemsis_submission_status_history",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "submission_id": str(sub_rec["id"]),
            "chart_id": chart_id,
            "from_status": None,
            "to_status": "pending",
            "actor": str(current.user_id),
            "occurred_at": now,
            "s3_bucket": xml_s3_bucket,
            "s3_key": xml_s3_key,
            "note": "submission_created",
        },
        typed_columns={
            "submission_id": str(sub_rec["id"]),
            "chart_id": chart_id,
            "to_status": "pending",
        },
        correlation_id=corr,
    )

    return sub_rec


# --------------------------------------------------------------------------- #
# GET /charts/{chart_id}/nemsis-submissions — list submissions for chart       #
# --------------------------------------------------------------------------- #
@router.get("/charts/{chart_id}/nemsis-submissions")
async def list_submissions(
    chart_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return (
        _svc(db)
        .repo("nemsis_submission_results")
        .list_raw_by_field(
            "chart_id",
            chart_id,
            limit=200,
        )
    )


# --------------------------------------------------------------------------- #
# GET /nemsis-submissions/{submission_id} — single submission + history        #
# --------------------------------------------------------------------------- #
@router.get("/nemsis-submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = svc.repo("nemsis_submission_results").get(
        tenant_id=current.tenant_id, record_id=submission_id
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    history = svc.repo("nemsis_submission_status_history").list_raw_by_field(
        "submission_id",
        submission_id,
        limit=200,
    )

    return {**rec, "status_history": history}


# --------------------------------------------------------------------------- #
# POST /nemsis-submissions/{id}/acknowledge                                    #
# --------------------------------------------------------------------------- #
@router.post("/nemsis-submissions/{submission_id}/acknowledge")
async def acknowledge_submission(
    submission_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _advance_status(
        submission_id=submission_id,
        to_status="acknowledged",
        payload=payload,
        request=request,
        current=current,
        db=db,
        s3_subfolder="ack",
        s3_content_type="application/xml",
        note_key="ack_note",
        s3_patch_keys=("ack_s3_bucket", "ack_s3_key"),
        timestamp_field="acknowledged_at",
    )


# --------------------------------------------------------------------------- #
# POST /nemsis-submissions/{id}/accept                                         #
# --------------------------------------------------------------------------- #
@router.post("/nemsis-submissions/{submission_id}/accept")
async def accept_submission(
    submission_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    result = await _advance_status(
        submission_id=submission_id,
        to_status="accepted",
        payload=payload,
        request=request,
        current=current,
        db=db,
        s3_subfolder="response",
        s3_content_type="application/xml",
        note_key="accept_note",
        s3_patch_keys=("response_s3_bucket", "response_s3_key"),
        timestamp_field="accepted_at",
        commit=False,
    )

    svc = _svc(db)
    sub_rec = svc.repo("nemsis_submission_results").get(
        tenant_id=current.tenant_id, record_id=submission_id
    )
    if sub_rec:
        chart_id = sub_rec.get("data", {}).get("chart_id")
        if chart_id:
            chart_rec = svc.repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
            if chart_rec:
                locked_data = {
                    **chart_rec.get("data", {}),
                    "chart_status": ChartStatus.LOCKED.value,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                lock_result = await svc.update(
                    table="epcr_charts",
                    tenant_id=current.tenant_id,
                    actor_user_id=current.user_id,
                    record_id=uuid.UUID(str(chart_rec["id"])),
                    expected_version=chart_rec["version"],
                    patch={"data": locked_data, "status": ChartStatus.LOCKED.value},
                    correlation_id=getattr(request.state, "correlation_id", None),
                    commit=False,
                )
                if lock_result is None:
                    db.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail="Chart version conflict — could not lock chart after acceptance",
                    )

    db.commit()
    return result


# --------------------------------------------------------------------------- #
# POST /nemsis-submissions/{id}/reject                                         #
# --------------------------------------------------------------------------- #
@router.post("/nemsis-submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _advance_status(
        submission_id=submission_id,
        to_status="rejected",
        payload=payload,
        request=request,
        current=current,
        db=db,
        s3_subfolder="response",
        s3_content_type="application/xml",
        note_key="reject_reason",
        s3_patch_keys=("response_s3_bucket", "response_s3_key"),
        timestamp_field="rejected_at",
    )


# --------------------------------------------------------------------------- #
# POST /nemsis-submissions/{id}/retry                                          #
# --------------------------------------------------------------------------- #
@router.post("/nemsis-submissions/{submission_id}/retry")
async def retry_submission(
    submission_id: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)

    orig_rec = svc.repo("nemsis_submission_results").get(
        tenant_id=current.tenant_id, record_id=submission_id
    )
    if orig_rec is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    orig_data = orig_rec.get("data", {})
    if orig_data.get("status") not in ("rejected",):
        raise HTTPException(
            status_code=422,
            detail="Only rejected submissions can be retried",
        )

    chart_id = orig_data.get("chart_id")
    chart_rec = svc.repo("epcr_charts").get(tenant_id=current.tenant_id, record_id=chart_id)
    if chart_rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")

    chart_data = chart_rec.get("data", {})
    xml_bytes = NEMSISExporter().export_chart(
        chart_data, agency_info=payload.get("agency_info", {})
    )
    sha256_hex = jcs_sha256({"xml_bytes_b64": xml_bytes.hex(), "chart_id": chart_id})

    new_submission_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    xml_s3_key = (
        f"nemsis-submissions/{current.tenant_id}/{chart_id}/{new_submission_id}/payload.xml"
    )
    try:
        xml_s3_bucket, xml_s3_key = _upload_to_s3(xml_bytes, xml_s3_key, "application/xml")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"S3 upload failed: {exc}") from exc

    prev_count = int(orig_data.get("attempt_count", 1))
    sub_data: dict[str, Any] = {
        "submission_id": new_submission_id,
        "chart_id": chart_id,
        "state_code": orig_data.get("state_code", ""),
        "endpoint_url": payload.get("endpoint_url") or orig_data.get("endpoint_url"),
        "status": "pending",
        "xml_s3_bucket": xml_s3_bucket,
        "xml_s3_key": xml_s3_key,
        "sha256_payload": sha256_hex,
        "attempt_count": prev_count + 1,
        "previous_submission_id": submission_id,
        "created_at": now,
        "updated_at": now,
    }

    new_rec = await svc.create(
        table="nemsis_submission_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=sub_data,
        typed_columns={
            "chart_id": chart_id,
            "state_code": orig_data.get("state_code", ""),
            "status": "pending",
        },
        correlation_id=corr,
    )

    await svc.create(
        table="nemsis_submission_status_history",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "submission_id": str(new_rec["id"]),
            "chart_id": chart_id,
            "from_status": None,
            "to_status": "pending",
            "actor": str(current.user_id),
            "occurred_at": now,
            "note": f"retry_of_{submission_id}",
            "s3_bucket": xml_s3_bucket,
            "s3_key": xml_s3_key,
        },
        typed_columns={
            "submission_id": str(new_rec["id"]),
            "chart_id": chart_id,
            "to_status": "pending",
        },
        correlation_id=corr,
    )

    return new_rec


# --------------------------------------------------------------------------- #
# Internal helper: advance status + optional S3 storage                        #
# --------------------------------------------------------------------------- #
async def _advance_status(
    *,
    submission_id: str,
    to_status: str,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser,
    db: Session,
    s3_subfolder: str,
    s3_content_type: str,
    note_key: str,
    s3_patch_keys: tuple[str, str],
    timestamp_field: str,
    commit: bool = True,
) -> dict:
    svc = _svc(db)
    corr = getattr(request.state, "correlation_id", None)

    rec = svc.repo("nemsis_submission_results").get(
        tenant_id=current.tenant_id, record_id=submission_id
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    rec_data = rec.get("data", {})
    current_status = rec_data.get("status", "pending")

    allowed = _VALID_TRANSITIONS.get(current_status, set())
    if to_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot transition from '{current_status}' to '{to_status}'",
        )

    now = datetime.now(UTC)
    now_iso = now.isoformat()
    chart_id = rec_data.get("chart_id", "")

    # Optional: store response document to S3
    s3_bucket: str | None = None
    s3_key_str: str | None = None
    response_content: bytes | None = payload.get("response_xml_bytes")
    if isinstance(response_content, str):
        response_content = _b64.b64decode(response_content)
    if response_content:
        s3_key_str = (
            f"nemsis-submissions/{current.tenant_id}/{chart_id}/{submission_id}/{s3_subfolder}.xml"
        )
        try:
            s3_bucket, s3_key_str = _upload_to_s3(response_content, s3_key_str, s3_content_type)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"S3 upload failed: {exc}") from exc

    patch_data = {
        **rec_data,
        "status": to_status,
        timestamp_field: now_iso,
        "updated_at": now_iso,
    }
    if s3_bucket:
        patch_data[s3_patch_keys[0]] = s3_bucket
        patch_data[s3_patch_keys[1]] = s3_key_str
    if payload.get("error_message"):
        patch_data["error_message"] = payload["error_message"]

    updated = await svc.update(
        table="nemsis_submission_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": patch_data, "status": to_status},
        correlation_id=corr,
        commit=False,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict")

    await svc.create(
        table="nemsis_submission_status_history",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "submission_id": submission_id,
            "chart_id": chart_id,
            "from_status": current_status,
            "to_status": to_status,
            "actor": str(current.user_id),
            "occurred_at": now_iso,
            "note": payload.get(note_key),
            "s3_bucket": s3_bucket,
            "s3_key": s3_key_str,
        },
        typed_columns={
            "submission_id": submission_id,
            "chart_id": chart_id,
            "to_status": to_status,
        },
        correlation_id=corr,
        commit=False,
    )

    if commit:
        db.commit()

    return updated
