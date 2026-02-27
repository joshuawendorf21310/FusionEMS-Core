from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.core.config import get_settings
from core_app.documents.s3_storage import put_bytes, presign_get, default_docs_bucket
from core_app.fax.cover_sheet import CoverSheetGenerator
from core_app.repositories.domination_repository import DominationRepository
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1", tags=["Doc Kit"])


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_tenant_info(svc: DominationService, tenant_id: uuid.UUID) -> dict:
    try:
        rows = svc.repo("tenants").list(tenant_id=tenant_id, limit=1)
        if rows:
            return rows[0].get("data") or {}
    except Exception:
        pass
    return {}


@router.post("/agency/doc-kit/generate")
async def generate_agency_doc_kit(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "agency_admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    settings = get_settings()

    tenant_data = _resolve_tenant_info(svc, current.tenant_id)
    agency_name = tenant_data.get("agency_name") or tenant_data.get("name") or "Unknown Agency"
    fax_number = tenant_data.get("billing_fax") or tenant_data.get("fax_number") or "N/A"
    inbound_email = tenant_data.get("billing_email") or tenant_data.get("email") or "billing@fusionemsquantum.com"
    upload_url = tenant_data.get("portal_url") or settings.api_base_url or "https://portal.fusionemsquantum.com"

    gen = CoverSheetGenerator()
    pdf_bytes = gen.generate_agency_doc_kit(
        agency_name=agency_name,
        tenant_id=str(current.tenant_id),
        fax_number=fax_number,
        inbound_email=inbound_email,
        upload_url=upload_url,
    )

    bucket = default_docs_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="docs_bucket_not_configured")

    ts = _timestamp_slug()
    s3_key = f"doc_kits/{current.tenant_id}/agency_doc_kit_{ts}.pdf"
    put_bytes(bucket=bucket, key=s3_key, content=pdf_bytes, content_type="application/pdf")

    pdf_record = await svc.create(
        table="documents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "doc_type": "agency_doc_kit",
            "bucket": bucket,
            "s3_key": s3_key,
            "generated_at": _utcnow(),
            "generator": "CoverSheetGenerator",
            "size_bytes": len(pdf_bytes),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    download_url = presign_get(bucket=bucket, key=s3_key, expires_seconds=300)

    return {
        "pdf_id": str(pdf_record["id"]),
        "s3_key": s3_key,
        "download_url": download_url,
    }


@router.post("/claims/{claim_id}/doc-kit/generate")
async def generate_claim_cover_sheet(
    claim_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "agency_admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    settings = get_settings()

    case = svc.repo("billing_cases").get(tenant_id=current.tenant_id, record_id=claim_id)
    if not case:
        raise HTTPException(status_code=404, detail="billing_case_not_found")
    cdata = case.get("data") or {}

    tenant_data = _resolve_tenant_info(svc, current.tenant_id)
    agency_name = tenant_data.get("agency_name") or tenant_data.get("name") or "Unknown Agency"
    fax_number = tenant_data.get("billing_fax") or tenant_data.get("fax_number") or "N/A"

    patient = cdata.get("patient") or {}
    first = patient.get("first_name") or cdata.get("patient_first_name") or ""
    last = patient.get("last_name") or cdata.get("patient_last_name") or ""
    patient_initials = (first[:1] + last[:1]).upper() if (first or last) else ""
    encounter_date = cdata.get("dos") or cdata.get("encounter_date") or ""
    doc_type = cdata.get("primary_doc_type") or "Other"

    gen = CoverSheetGenerator()
    pdf_bytes = gen.generate_claim_cover_sheet(
        claim_id=str(claim_id),
        tenant_id=str(current.tenant_id),
        doc_type=doc_type,
        agency_name=agency_name,
        fax_number=fax_number,
        patient_initials=patient_initials,
        encounter_date=encounter_date,
    )

    bucket = default_docs_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="docs_bucket_not_configured")

    ts = _timestamp_slug()
    s3_key = f"doc_kits/{current.tenant_id}/claims/{claim_id}/cover_sheet_{ts}.pdf"
    put_bytes(bucket=bucket, key=s3_key, content=pdf_bytes, content_type="application/pdf")

    pdf_record = await svc.create(
        table="documents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "doc_type": "claim_cover_sheet",
            "owner_entity_type": "billing_case",
            "owner_entity_id": str(claim_id),
            "bucket": bucket,
            "s3_key": s3_key,
            "generated_at": _utcnow(),
            "generator": "CoverSheetGenerator",
            "size_bytes": len(pdf_bytes),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    download_url = presign_get(bucket=bucket, key=s3_key, expires_seconds=300)

    return {
        "pdf_id": str(pdf_record["id"]),
        "s3_key": s3_key,
        "download_url": download_url,
    }


@router.get("/claims/{claim_id}/doc-kit/latest")
async def get_latest_claim_cover_sheet(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "agency_admin", "ems"])
    svc = DominationService(db, get_event_publisher())

    repo = DominationRepository(db, table="documents")
    all_docs = repo.list_raw_by_field("doc_type", "claim_cover_sheet", limit=200)
    claim_docs = [
        d for d in all_docs
        if (d.get("data") or {}).get("owner_entity_id") == str(claim_id)
        and str(d.get("tenant_id", "")) == str(current.tenant_id)
    ]
    if not claim_docs:
        raise HTTPException(status_code=404, detail="no_cover_sheet_found")

    claim_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    latest = claim_docs[0]
    ldata = latest.get("data") or {}

    bucket = ldata.get("bucket", "")
    s3_key = ldata.get("s3_key", "")
    download_url = presign_get(bucket=bucket, key=s3_key, expires_seconds=300) if bucket and s3_key else None

    return {
        "pdf_id": str(latest["id"]),
        "s3_key": s3_key,
        "generated_at": ldata.get("generated_at"),
        "size_bytes": ldata.get("size_bytes"),
        "download_url": download_url,
    }
