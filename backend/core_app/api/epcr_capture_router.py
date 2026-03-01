from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.epcr.capture_service import CaptureService
from core_app.epcr.ocr_ingestion import EPCROcrService
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/epcr", tags=["ePCR Capture"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _get_chart(svc: DominationService, tenant_id: uuid.UUID, chart_id: str) -> dict[str, Any]:
    rec = svc.repo("epcr_charts").get(tenant_id=tenant_id, record_id=chart_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return rec


async def _append_attachment_to_chart(
    svc: DominationService,
    rec: dict[str, Any],
    attachment: dict[str, Any],
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    correlation_id: str | None,
) -> None:
    updated_data = dict(rec["data"])
    updated_data.setdefault("attachments", []).append(attachment)
    updated_data["updated_at"] = datetime.now(UTC).isoformat()
    await svc.update(
        table="epcr_charts",
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        record_id=uuid.UUID(str(rec["id"])),
        expected_version=rec["version"],
        patch={"data": updated_data},
        correlation_id=correlation_id,
    )


@router.post("/charts/{chart_id}/ocr/facesheet")
async def ocr_facesheet(
    chart_id: str,
    request: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = _get_chart(svc, current.tenant_id, chart_id)
    content = await file.read()
    correlation_id = getattr(request.state, "correlation_id", None)

    result = EPCROcrService(get_settings().s3_bucket_docs).ingest_facesheet(
        content=content,
        filename=file.filename or "facesheet",
        chart_id=chart_id,
        tenant_id=str(current.tenant_id),
    )

    attachment = {
        "attachment_id": result["ocr_job_id"],
        "attachment_type": "facesheet",
        "s3_key": result["s3_key"],
        "filename": file.filename or "facesheet",
        "uploaded_at": result["processed_at"],
    }
    await _append_attachment_to_chart(
        svc, rec, attachment, current.tenant_id, current.user_id, correlation_id
    )

    await svc.create(
        table="epcr_ocr_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "chart_id": chart_id, "ocr_type": "facesheet"},
        correlation_id=correlation_id,
    )
    return result


@router.post("/charts/{chart_id}/ocr/transport-paperwork")
async def ocr_transport_paperwork(
    chart_id: str,
    request: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = _get_chart(svc, current.tenant_id, chart_id)
    content = await file.read()
    correlation_id = getattr(request.state, "correlation_id", None)

    result = EPCROcrService(get_settings().s3_bucket_docs).ingest_transport_paperwork(
        content=content,
        filename=file.filename or "transport_paperwork",
        chart_id=chart_id,
        tenant_id=str(current.tenant_id),
    )

    attachment = {
        "attachment_id": result["ocr_job_id"],
        "attachment_type": "transport_paperwork",
        "s3_key": result["s3_key"],
        "filename": file.filename or "transport_paperwork",
        "uploaded_at": result["processed_at"],
    }
    await _append_attachment_to_chart(
        svc, rec, attachment, current.tenant_id, current.user_id, correlation_id
    )

    await svc.create(
        table="epcr_ocr_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "chart_id": chart_id, "ocr_type": "transport_paperwork"},
        correlation_id=correlation_id,
    )
    return result


@router.post("/charts/{chart_id}/capture/rhythm-strip")
async def capture_rhythm_strip(
    chart_id: str,
    request: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = _get_chart(svc, current.tenant_id, chart_id)
    content = await file.read()
    correlation_id = getattr(request.state, "correlation_id", None)

    result = CaptureService(get_settings().s3_bucket_docs).process_rhythm_strip(
        content=content,
        filename=file.filename or "rhythm_strip",
        chart_id=chart_id,
        tenant_id=str(current.tenant_id),
    )

    attachment = {
        "attachment_id": result["capture_id"],
        "attachment_type": "rhythm_strip",
        "s3_key": result["s3_key"],
        "filename": result["filename"],
        "uploaded_at": result["captured_at"],
    }
    await _append_attachment_to_chart(
        svc, rec, attachment, current.tenant_id, current.user_id, correlation_id
    )

    await svc.create(
        table="epcr_capture_sessions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "chart_id": chart_id},
        correlation_id=correlation_id,
    )
    return result


@router.post("/charts/{chart_id}/capture/pump-screen")
async def capture_pump_screen(
    chart_id: str,
    request: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = _get_chart(svc, current.tenant_id, chart_id)
    content = await file.read()
    correlation_id = getattr(request.state, "correlation_id", None)

    result = CaptureService(get_settings().s3_bucket_docs).process_pump_screen(
        content=content,
        filename=file.filename or "pump_screen",
        chart_id=chart_id,
        tenant_id=str(current.tenant_id),
    )

    attachment = {
        "attachment_id": result["capture_id"],
        "attachment_type": "pump_screen",
        "s3_key": result["s3_key"],
        "filename": result["filename"],
        "uploaded_at": result["captured_at"],
    }
    await _append_attachment_to_chart(
        svc, rec, attachment, current.tenant_id, current.user_id, correlation_id
    )

    await svc.create(
        table="epcr_capture_sessions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "chart_id": chart_id},
        correlation_id=correlation_id,
    )
    return result


@router.post("/charts/{chart_id}/capture/vent-screen")
async def capture_vent_screen(
    chart_id: str,
    request: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rec = _get_chart(svc, current.tenant_id, chart_id)
    content = await file.read()
    correlation_id = getattr(request.state, "correlation_id", None)

    result = CaptureService(get_settings().s3_bucket_docs).process_vent_screen(
        content=content,
        filename=file.filename or "vent_screen",
        chart_id=chart_id,
        tenant_id=str(current.tenant_id),
    )

    attachment = {
        "attachment_id": result["capture_id"],
        "attachment_type": "vent_screen",
        "s3_key": result["s3_key"],
        "filename": result["filename"],
        "uploaded_at": result["captured_at"],
    }
    await _append_attachment_to_chart(
        svc, rec, attachment, current.tenant_id, current.user_id, correlation_id
    )

    await svc.create(
        table="epcr_capture_sessions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "chart_id": chart_id},
        correlation_id=correlation_id,
    )
    return result
