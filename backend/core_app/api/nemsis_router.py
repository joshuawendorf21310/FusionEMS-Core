from __future__ import annotations

import uuid
import base64
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.compliance.nemsis_xml_generator import build_nemsis_document, validate_nemsis_xml

router = APIRouter(prefix="/api/v1/nemsis", tags=["NEMSIS"])


@router.post("/validate")
async def validate(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    result: dict[str, Any] = {"status": "queued", "input": payload}

    if payload.get("incident") and payload.get("patient"):
        xml_bytes = build_nemsis_document(
            incident=payload["incident"],
            patient=payload["patient"],
            vitals=payload.get("vitals", []),
            agency_info=payload.get("agency", {}),
        )
        validation = validate_nemsis_xml(xml_bytes)
        result = {
            "status": "validated" if validation["valid"] else "invalid",
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        }

    return await svc.create(
        table="nemsis_validation_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=result,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/exports")
async def create_export(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())

    xml_b64: str | None = None
    generation_error: str | None = None

    incident = payload.get("incident")
    patient = payload.get("patient")

    if incident and patient:
        try:
            xml_bytes = build_nemsis_document(
                incident=incident,
                patient=patient,
                vitals=payload.get("vitals", []),
                agency_info=payload.get("agency", {}),
            )
            xml_b64 = base64.b64encode(xml_bytes).decode()
        except Exception as exc:
            generation_error = str(exc)

    job: dict[str, Any] = {
        "status": "completed" if xml_b64 else ("failed" if generation_error else "queued"),
        "range": payload.get("range"),
        "agency": payload.get("agency"),
        "xml_b64": xml_b64,
        "error": generation_error,
    }

    return await svc.create(
        table="nemsis_export_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=job,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/exports/{job_id}/download")
async def download_export(
    job_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("nemsis_export_jobs").get(tenant_id=current.tenant_id, record_id=job_id)
    if not rec:
        return {"error": "not_found"}

    xml_b64 = rec.get("data", {}).get("xml_b64")
    if not xml_b64:
        return {"error": "xml_not_available", "status": rec.get("data", {}).get("status")}

    xml_bytes = base64.b64decode(xml_b64)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=nemsis_{job_id}.xml"},
    )


@router.get("/exports/{job_id}")
async def get_export(
    job_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("nemsis_export_jobs").get(tenant_id=current.tenant_id, record_id=job_id)
    if not rec:
        return {"error": "not_found"}
    data = rec.get("data", {})
    return {
        "id": str(job_id),
        "status": data.get("status"),
        "range": data.get("range"),
        "agency": data.get("agency"),
        "error": data.get("error"),
        "has_xml": bool(data.get("xml_b64")),
    }
