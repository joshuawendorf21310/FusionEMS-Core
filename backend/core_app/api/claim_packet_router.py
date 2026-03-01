from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.builders.claim_packet_generator import ClaimPacketGenerator
from core_app.documents.s3_storage import default_docs_bucket, presign_get, put_bytes
from core_app.repositories.domination_repository import DominationRepository
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/claims", tags=["Claim Packets"])


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _timestamp_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _load_claim_bundle(
    svc: DominationService,
    tenant_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> tuple[dict, dict, list[dict]]:
    case = svc.repo("billing_cases").get(tenant_id=tenant_id, record_id=claim_id)
    if not case:
        raise HTTPException(status_code=404, detail="billing_case_not_found")
    cdata = case.get("data") or {}

    patient_raw = cdata.get("patient") or {}
    patient_data = {
        "first_name": patient_raw.get("first_name") or cdata.get("patient_first_name") or "",
        "last_name": patient_raw.get("last_name") or cdata.get("patient_last_name") or "",
        "dob": patient_raw.get("dob") or cdata.get("patient_dob") or "",
        "gender": patient_raw.get("sex") or patient_raw.get("gender") or cdata.get("patient_gender") or "",
    }

    claim_data = {
        **cdata,
        "claim_id": str(case.get("id")),
        "agency_name": cdata.get("billing_name") or "Unknown Agency",
    }

    all_docs = svc.repo("documents").list_raw_by_field("owner_entity_id", str(claim_id), limit=100)
    attachments: list[dict] = []
    for d in all_docs:
        dd = d.get("data") or {}
        if dd.get("owner_entity_type") == "billing_case":
            attachments.append({
                "doc_type": dd.get("doc_type") or "N/A",
                "filename": dd.get("filename") or dd.get("s3_key") or "",
                "s3_key": dd.get("s3_key") or "",
                "received_date": str(d.get("created_at", "")),
                "sha256": dd.get("sha256") or "",
            })

    return claim_data, patient_data, attachments


@router.post("/{claim_id}/packet/generate")
async def generate_claim_packet(
    claim_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing", "agency_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    claim_data, patient_data, attachments = _load_claim_bundle(svc, current.tenant_id, claim_id)

    gen = ClaimPacketGenerator()
    pdf_bytes = gen.generate_claim_packet(
        claim_data=claim_data,
        patient_data=patient_data,
        attachments=attachments,
        include_audit=True,
    )

    bucket = default_docs_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="docs_bucket_not_configured")

    ts = _timestamp_slug()
    s3_key = f"claim_packets/{current.tenant_id}/{claim_id}/packet_{ts}.pdf"
    put_bytes(bucket=bucket, key=s3_key, content=pdf_bytes, content_type="application/pdf")

    pdf_record = await svc.create(
        table="documents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "doc_type": "claim_packet",
            "owner_entity_type": "billing_case",
            "owner_entity_id": str(claim_id),
            "bucket": bucket,
            "s3_key": s3_key,
            "generated_at": _utcnow(),
            "generator": "ClaimPacketGenerator",
            "size_bytes": len(pdf_bytes),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    download_url = presign_get(bucket=bucket, key=s3_key, expires_seconds=300)

    page_count: int | None = None
    try:
        if pdf_bytes[:4] == b"%PDF":
            page_count = pdf_bytes.count(b"/Page\n") + pdf_bytes.count(b"/Page ")
    except Exception:
        pass

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.claim.packet.generated",
        tenant_id=current.tenant_id,
        entity_id=claim_id,
        entity_type="claim_packet",
        event_type="CLAIM_PACKET_GENERATED",
        payload={"pdf_id": str(pdf_record["id"]), "claim_id": str(claim_id), "s3_key": s3_key},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    return {
        "pdf_id": str(pdf_record["id"]),
        "s3_key": s3_key,
        "download_url": download_url,
        "page_count": page_count,
    }


@router.get("/{claim_id}/packet/latest")
async def get_latest_claim_packet(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing", "agency_admin", "ems"):
        raise HTTPException(status_code=403, detail="Forbidden")
    repo = DominationRepository(db, table="documents")
    all_docs = repo.list_raw_by_field("doc_type", "claim_packet", limit=200)
    claim_packets = [
        d for d in all_docs
        if (d.get("data") or {}).get("owner_entity_id") == str(claim_id)
        and str(d.get("tenant_id", "")) == str(current.tenant_id)
    ]
    if not claim_packets:
        raise HTTPException(status_code=404, detail="no_claim_packet_found")

    claim_packets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    latest = claim_packets[0]
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


@router.post("/{claim_id}/packet/{pdf_id}/download")
async def download_claim_packet(
    claim_id: uuid.UUID,
    pdf_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if current.role not in ("founder", "admin", "billing", "agency_admin", "ems"):
        raise HTTPException(status_code=403, detail="Forbidden")
    repo = DominationRepository(db, table="documents")
    record = repo.get(tenant_id=current.tenant_id, record_id=pdf_id)
    if not record:
        raise HTTPException(status_code=404, detail="pdf_record_not_found")

    rdata = record.get("data") or {}
    if rdata.get("owner_entity_id") != str(claim_id):
        raise HTTPException(status_code=404, detail="pdf_record_not_found")

    bucket = rdata.get("bucket", "")
    s3_key = rdata.get("s3_key", "")
    if not bucket or not s3_key:
        raise HTTPException(status_code=404, detail="no_s3_key_on_record")

    download_url = presign_get(bucket=bucket, key=s3_key, expires_seconds=300)
    return {"pdf_id": str(pdf_id), "download_url": download_url, "expires_in_seconds": 300}
