from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.imports.vendor_parsers import parse_vendor_csv, parse_vendor_xml, detect_vendor, score_import_completeness

router = APIRouter(prefix="/api/v1/imports", tags=['Imports'])


@router.post("/create")
async def create_batch(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="import_batches", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=payload, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/{batch_id}/upload-url")
async def upload(batch_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user)):
    return {"batch_id": str(batch_id), "method":"PUT", "url": payload.get("url") or ""}

@router.post("/{batch_id}/map")
async def map_batch(batch_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    data = {"batch_id": str(batch_id), "mapping": payload}
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="import_mappings", tenant_id=current.tenant_id, actor_user_id=current.user_id, data=data, correlation_id=getattr(request.state,"correlation_id",None))

@router.post("/{batch_id}/run")
async def run_batch(batch_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(table="import_errors", tenant_id=current.tenant_id, actor_user_id=current.user_id, data={"batch_id": str(batch_id), "status":"queued"}, correlation_id=getattr(request.state,"correlation_id",None))


@router.post("/vendor/parse")
async def parse_vendor_file(
    file: UploadFile = File(...),
    vendor_hint: str | None = None,
    current: CurrentUser = Depends(get_current_user),
):
    """Parse a vendor CSV or XML export and return normalised records with completeness scoring."""
    content = await file.read()
    filename = file.filename or ""

    if filename.lower().endswith(".xml"):
        result = parse_vendor_xml(content, vendor_hint=vendor_hint)
    elif filename.lower().endswith(".csv"):
        result = parse_vendor_csv(content, vendor_hint=vendor_hint)
    else:
        content_type = file.content_type or ""
        if "xml" in content_type:
            result = parse_vendor_xml(content, vendor_hint=vendor_hint)
        else:
            result = parse_vendor_csv(content, vendor_hint=vendor_hint)

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    completeness = score_import_completeness(result.get("records", []))
    return {**result, "completeness": completeness}


@router.post("/vendor/detect")
async def detect_vendor_endpoint(
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
):
    """Detect the vendor format from the first row of a CSV upload."""
    content = await file.read()
    import csv
    import io

    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    headers = list(rows[0].keys()) if rows else []
    vendor = detect_vendor(headers)
    return {"vendor": vendor, "headers": headers, "row_count": len(rows)}
