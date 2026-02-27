from __future__ import annotations

import base64
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.billing.validation import BillingValidator
from core_app.billing.x12_837p import build_837p_ambulance
from core_app.billing.x12_835 import parse_835
from core_app.billing.artifacts import store_edi_artifact
from core_app.core.config import get_settings
from core_app.documents.s3_storage import put_bytes, presign_get, default_exports_bucket
from core_app.integrations.officeally import OfficeAllySftpConfig, submit_837_via_sftp, OfficeAllyClientError
from core_app.payments.stripe_service import StripeConfig, create_patient_checkout_session, verify_webhook_signature, StripeNotConfigured
from core_app.fax.telnyx_service import TelnyxConfig, send_sms, TelnyxNotConfigured
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.billing.ar_aging import compute_ar_aging, compute_revenue_forecast

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


class SubmitOfficeAllyRequest(BaseModel):
    submitter_id: str = Field(..., description="X12 ISA/GS sender id")
    receiver_id: str = Field(..., description="X12 receiver id")
    billing_npi: str
    billing_tax_id: str
    service_lines: list[dict[str, Any]] = Field(default_factory=list)


class EraImportRequest(BaseModel):
    x12_base64: str


class PaymentLinkRequest(BaseModel):
    account_id: uuid.UUID
    amount_cents: int
    patient_phone: str
    success_url: str
    cancel_url: str


@router.post("/cases/{case_id}/validate")
async def validate_case(
    case_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    validator = BillingValidator(db, tenant_id=current.tenant_id)

    try:
        result = validator.validate_case(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="billing_case_not_found")

    missing = result["missing_docs"]

    # Create missing-doc tasks idempotently: (case_id, doc_type)
    created_tasks: list[dict[str, Any]] = []
    existing = svc.repo("missing_document_tasks").list(tenant_id=current.tenant_id, limit=5000)
    existing_keys = {(t["data"].get("owner_entity_id"), t["data"].get("doc_type")) for t in existing}

    for doc_type in missing:
        key = (str(case_id), doc_type)
        if key in existing_keys:
            continue
        task = await svc.create(
            table="missing_document_tasks",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "owner_entity_type": "billing_case",
                "owner_entity_id": str(case_id),
                "doc_type": doc_type,
                "status": "open",
                "created_reason": "billing_prevalidation",
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        created_tasks.append(task)

    payload = {
        "case_id": str(case_id),
        "missing_docs": missing,
        "risk_score": result["risk_score"],
        "risk_flags": result["risk_flags"],
        "created_task_ids": [t["id"] for t in created_tasks],
    }
    publisher.publish(
        topic=f"tenant.{current.tenant_id}.billing.case.validated",
        tenant_id=current.tenant_id,
        entity_type="billing_case",
        entity_id=str(case_id),
        event_type="BILLING_CASE_VALIDATED",
        payload=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return payload


@router.post("/cases/{case_id}/submit-officeally")
async def submit_officeally(
    case_id: uuid.UUID,
    body: SubmitOfficeAllyRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Generates an 837 artifact, stores it in S3 (exports bucket), records an edi_artifact row,
    and optionally uploads via Office Ally SFTP if configured.
    """
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    case = svc.repo("billing_cases").get(tenant_id=current.tenant_id, record_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="billing_case_not_found")

    # Resolve patient + claim info from stored JSON (minimal required fields)
    patient = case["data"].get("patient", {})
    claim = {
        "claim_id": case["data"].get("claim_id", str(case_id)),
        "dos": case["data"].get("dos"),
        "member_id": case["data"].get("member_id", ""),
        "billing_name": case["data"].get("billing_name", "FUSIONEMSQUANTUM"),
        "billing_address1": case["data"].get("billing_address1", "UNKNOWN"),
        "billing_city": case["data"].get("billing_city", "UNKNOWN"),
        "billing_state": case["data"].get("billing_state", "WI"),
        "billing_zip": case["data"].get("billing_zip", "00000"),
        "submitter_name": case["data"].get("submitter_name", "FUSIONEMSQUANTUM"),
        "submitter_contact": case["data"].get("submitter_contact", "BILLING"),
        "submitter_phone": case["data"].get("submitter_phone", "0000000000"),
        "receiver_name": "OFFICEALLY",
    }

    x12_text, env = build_837p_ambulance(
        submitter_id=body.submitter_id,
        receiver_id=body.receiver_id,
        billing_npi=body.billing_npi,
        billing_tax_id=body.billing_tax_id,
        patient=patient,
        claim=claim,
        service_lines=body.service_lines or case["data"].get("service_lines", []),
    )
    file_name = f"837P_{case_id}_{env.isa_control}.x12"
    artifact = store_edi_artifact(
        db=db,
        tenant_id=current.tenant_id,
        artifact_type="837",
        file_name=file_name,
        content=x12_text.encode("utf-8"),
        content_type="text/plain",
    )

    edi_row = await svc.create(
        table="edi_artifacts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "billing_case_id": str(case_id),
            "type": "837P",
            "bucket": artifact["bucket"],
            "key": artifact["key"],
            "isa_control": env.isa_control,
            "gs_control": env.gs_control,
            "st_control": env.st_control,
            "status": "stored",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    # Attempt SFTP upload if configured
    settings = get_settings()
    uploaded_path = None
    if settings.officeally_sftp_host and settings.officeally_sftp_username:
        try:
            cfg = OfficeAllySftpConfig(
                host=settings.officeally_sftp_host,
                port=settings.officeally_sftp_port,
                username=settings.officeally_sftp_username,
                password=settings.officeally_sftp_password,
                remote_dir=settings.officeally_sftp_remote_dir or "/",
            )
            uploaded_path = submit_837_via_sftp(cfg=cfg, file_name=file_name, x12_bytes=x12_text.encode("utf-8"))
            await svc.update(
                table="edi_artifacts",
                tenant_id=current.tenant_id,
                entity_id=edi_row["id"],
                actor_user_id=current.user_id,
                expected_version=edi_row["version"],
                data_patch={"status": "uploaded", "officeally_remote_path": uploaded_path},
                correlation_id=getattr(request.state, "correlation_id", None),
            )
        except OfficeAllyClientError as e:
            await svc.update(
                table="edi_artifacts",
                tenant_id=current.tenant_id,
                entity_id=edi_row["id"],
                actor_user_id=current.user_id,
                expected_version=edi_row["version"],
                data_patch={"status": "upload_failed", "error": str(e)},
                correlation_id=getattr(request.state, "correlation_id", None),
            )

    publisher.publish(
        topic=f"tenant.{current.tenant_id}.billing.edi.837.created",
        tenant_id=current.tenant_id,
        entity_type="edi_artifact",
        entity_id=edi_row["id"],
        event_type="EDI_837_CREATED",
        payload={"billing_case_id": str(case_id), "edi_artifact_id": edi_row["id"], "uploaded_path": uploaded_path},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"edi_artifact": edi_row, "download_url": artifact["download_url"], "officeally_uploaded_path": uploaded_path}


@router.post("/eras/import")
async def import_era(
    body: EraImportRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    try:
        x12 = base64.b64decode(body.x12_base64.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_base64")

    parsed = parse_835(x12)

    # Store ERA artifact to S3 for audit
    bucket = default_exports_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="exports_bucket_not_configured")
    key = f"tenants/{current.tenant_id}/edi/835/ERA_{uuid.uuid4()}.x12"
    put_bytes(bucket=bucket, key=key, content=x12.encode("utf-8"), content_type="text/plain")
    era_row = await svc.create(
        table="eras",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"bucket": bucket, "key": key, "denials_count": len(parsed["denials"])},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    for d in parsed["denials"]:
        await svc.create(
            table="denials",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "era_id": era_row["id"],
                "claim_id": d["claim_id"],
                "group_code": d["group_code"],
                "reason_code": d["reason_code"],
                "amount": d["amount"],
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )

    publisher.publish(
        topic=f"tenant.{current.tenant_id}.billing.era.imported",
        tenant_id=current.tenant_id,
        entity_type="era",
        entity_id=era_row["id"],
        event_type="ERA_IMPORTED",
        payload={"era_id": era_row["id"], "denials_count": len(parsed["denials"])},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"era": era_row, "denials": parsed["denials"], "download_url": presign_get(bucket=bucket, key=key)}


@router.post("/claims/{claim_id}/appeal/generate")
async def generate_appeal(
    claim_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Generates a deterministic appeal letter (text) and stores it as an export artifact.
    """
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    claim = svc.repo("claims").get(tenant_id=current.tenant_id, record_id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="claim_not_found")

    bucket = default_exports_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="exports_bucket_not_configured")

    denial_reason = claim["data"].get("denial_reason", "Denial reason not recorded.")
    payer = claim["data"].get("payer_name", "PAYER")
    patient = claim["data"].get("patient_name", "PATIENT")
    dos = claim["data"].get("dos", "UNKNOWN")

    letter = (
        f"APPEAL LETTER\n"
        f"Payer: {payer}\n"
        f"Patient: {patient}\n"
        f"Date of Service: {dos}\n"
        f"Claim ID: {claim_id}\n\n"
        f"This letter serves as a formal appeal for the denial of the above claim.\n"
        f"Denial stated: {denial_reason}\n\n"
        f"We request reconsideration and reprocessing of this claim based on documented medical necessity,\n"
        f"appropriate coding, and supporting documentation on file.\n\n"
        f"Sincerely,\nFusionEMS Quantum Billing\n"
    )
    key = f"tenants/{current.tenant_id}/appeals/appeal_{claim_id}.txt"
    put_bytes(bucket=bucket, key=key, content=letter.encode("utf-8"), content_type="text/plain")

    appeal_row = await svc.create(
        table="appeals",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"claim_id": str(claim_id), "bucket": bucket, "key": key, "status": "generated"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    publisher.publish(
        topic=f"tenant.{current.tenant_id}.billing.appeal.generated",
        tenant_id=current.tenant_id,
        entity_type="appeal",
        entity_id=appeal_row["id"],
        event_type="APPEAL_GENERATED",
        payload={"appeal_id": appeal_row["id"], "claim_id": str(claim_id)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"appeal": appeal_row, "download_url": presign_get(bucket=bucket, key=key)}


@router.post("/payment/link")
async def create_payment_link(
    body: PaymentLinkRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Stripe-only: creates a hosted checkout session and sends the link via Telnyx SMS.
    Stores ONLY Stripe session IDs/status.
    """
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    settings = get_settings()

    # Stripe session
    try:
        sess = create_patient_checkout_session(
            cfg=StripeConfig(secret_key=settings.stripe_secret_key, webhook_secret=settings.stripe_webhook_secret or None),
            amount_cents=body.amount_cents,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            metadata={"tenant_id": current.tenant_id, "account_id": str(body.account_id)},
        )
    except StripeNotConfigured as e:
        raise HTTPException(status_code=500, detail=str(e))

    link_row = await svc.create(
        table="patient_payment_links",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"account_id": str(body.account_id), "amount_cents": body.amount_cents, "stripe_session_id": sess["id"], "status": "created"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    # Send SMS
    try:
        tel = TelnyxConfig(api_key=settings.telnyx_api_key, messaging_profile_id=settings.telnyx_messaging_profile_id or None)
        send_sms(cfg=tel, from_number=settings.telnyx_from_number, to_number=body.patient_phone, text=f"Your payment link: {sess['url']}")
    except TelnyxNotConfigured as e:
        # SMS failure shouldn't delete payment link
        await svc.update(
            table="patient_payment_links",
            tenant_id=current.tenant_id,
            entity_id=link_row["id"],
            actor_user_id=current.user_id,
            expected_version=link_row["version"],
            data_patch={"status": "sms_failed", "sms_error": str(e)},
            correlation_id=getattr(request.state, "correlation_id", None),
        )

    publisher.publish(
        topic=f"tenant.{current.tenant_id}.billing.payment_link.created",
        tenant_id=current.tenant_id,
        entity_type="patient_payment_link",
        entity_id=link_row["id"],
        event_type="PAYMENT_LINK_CREATED",
        payload={"payment_link_id": link_row["id"], "stripe_session_id": sess["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"payment_link": link_row, "stripe": sess}


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    current: CurrentUser = Depends(get_current_user),  # protected endpoint; public webhook should be separate path in pricing_router
    db: Session = Depends(db_session_dependency),
):
    raise HTTPException(status_code=400, detail="Use /api/v1/public/webhooks/stripe")


@router.get("/ar-aging")
async def get_ar_aging(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    report = compute_ar_aging(db, current.tenant_id)
    return {
        "as_of_date": report.as_of_date,
        "total_ar_cents": report.total_ar_cents,
        "total_claims": report.total_claims,
        "avg_days_in_ar": report.avg_days_in_ar,
        "buckets": [
            {"label": b.label, "count": b.count, "total_cents": b.total_cents}
            for b in report.buckets
        ],
        "payer_breakdown": report.payer_breakdown,
    }


@router.get("/revenue-forecast")
async def get_revenue_forecast(
    months: int = 3,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    return compute_revenue_forecast(db, current.tenant_id, months=months)
