from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.documents.ocr import TextractOcrService
from core_app.documents.s3_storage import default_docs_bucket
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


class ProcessRequest(BaseModel):
    document_id: uuid.UUID


@router.post("/upload-url")
async def upload_url(payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user)):
    """
    Returns a presigned PUT URL for uploading a document into the docs bucket.
    Client uploads directly to S3; backend stores metadata via /documents/{id}/attach.
    """
    bucket = default_docs_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="docs_bucket_not_configured")
    key = f"tenants/{current.tenant_id}/uploads/{uuid.uuid4()}.bin"
    import boto3
    s3 = boto3.client("s3")
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": payload.get("content_type", "application/octet-stream")},
        ExpiresIn=900,
    )
    return {"method": "PUT", "url": url, "bucket": bucket, "key": key, "headers": {"Content-Type": payload.get("content_type", "application/octet-stream")}}


@router.post("/process")
async def process(body: ProcessRequest, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    """
    Starts Textract OCR for a stored S3 document.
    Requires documents table record contains bucket + s3_key.
    """
    require_role(current, ["founder","billing","admin","dispatcher","ems","fire","hems"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    doc = svc.repo("documents").get(tenant_id=current.tenant_id, record_id=body.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document_not_found")
    bucket = doc["data"].get("bucket") or default_docs_bucket()
    s3_key = doc["data"].get("s3_key")
    if not bucket or not s3_key:
        raise HTTPException(status_code=400, detail="document_missing_s3_ref")

    ocr = TextractOcrService(db, tenant_id=current.tenant_id, bucket=bucket)
    extraction = ocr.start_job(document_id=str(body.document_id), s3_key=s3_key)

    publisher.publish(
        topic=f"tenant.{current.tenant_id}.documents.ocr.started",
        tenant_id=current.tenant_id,
        entity_type="document",
        entity_id=str(body.document_id),
        event_type="OCR_STARTED",
        payload={"document_id": str(body.document_id), "extraction_id": extraction["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return extraction


@router.get("/{document_id}")
async def get_doc(document_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("documents").get(tenant_id=current.tenant_id, record_id=document_id)
    return rec or {"error": "not_found"}


@router.post("/{document_id}/attach")
async def attach(document_id: uuid.UUID, payload: dict[str, Any], request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    """
    Attaches uploaded S3 object metadata to the documents table.
    payload must include bucket, key, doc_type (optional).
    """
    require_role(current, ["founder","billing","admin","dispatcher","ems","fire","hems","facility_user"])
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="documents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "bucket": payload.get("bucket"),
            "s3_key": payload.get("key"),
            "doc_type": payload.get("doc_type", "other"),
            "owner_entity_type": payload.get("owner_entity_type"),
            "owner_entity_id": payload.get("owner_entity_id"),
            "status": "uploaded",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.post("/extractions/{extraction_id}/refresh")
async def refresh_extraction(extraction_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    """
    Poll Textract job status and store results.
    """
    require_role(current, ["founder","billing","admin"])
    # Determine bucket from doc record in extraction
    ex_repo = DominationService(db, get_event_publisher()).repo("document_extractions")
    ex = ex_repo.get(tenant_id=current.tenant_id, record_id=extraction_id)
    if not ex:
        raise HTTPException(status_code=404, detail="extraction_not_found")
    doc_id = ex["data"].get("document_id")
    doc = DominationService(db, get_event_publisher()).repo("documents").get(tenant_id=current.tenant_id, record_id=uuid.UUID(str(doc_id))) if doc_id else None
    bucket = (doc or {}).get("data", {}).get("bucket") or default_docs_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="docs_bucket_not_configured")

    ocr = TextractOcrService(db, tenant_id=current.tenant_id, bucket=bucket)
    updated = ocr.poll_job(extraction_id=str(extraction_id))
    return updated
