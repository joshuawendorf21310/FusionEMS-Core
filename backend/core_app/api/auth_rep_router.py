from __future__ import annotations

import hashlib
import hmac
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.fax.telnyx_service import TelnyxConfig, send_sms, TelnyxNotConfigured
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.realtime_events import emit_authorization_verified
from core_app.services.ses_service import get_ses_service

router = APIRouter(prefix="/api/v1/auth-rep", tags=["Authorization Representative"])

OTP_EXPIRY_MINUTES = 10


def _generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


class RepRegistrationRequest(BaseModel):
    patient_account_id: uuid.UUID
    relationship: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    delivery_method: str = "sms"


class OtpVerifyRequest(BaseModel):
    session_id: uuid.UUID
    otp_code: str


class RepDocumentUploadRequest(BaseModel):
    session_id: uuid.UUID
    document_type: str
    s3_key: str
    notes: str = ""


@router.post("/register")
async def register_rep(
    payload: RepRegistrationRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    otp_code = _generate_otp()
    session_id = uuid.uuid4()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    await svc.create(
        table="auth_rep_sessions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "session_id": str(session_id),
            "patient_account_id": str(payload.patient_account_id),
            "relationship": payload.relationship,
            "full_name": payload.full_name,
            "email": payload.email,
            "phone": payload.phone,
            "delivery_method": payload.delivery_method,
            "otp_hash": hashlib.sha256(otp_code.encode()).hexdigest(),
            "attempts": 0,
            "otp_expires_at": expires_at,
            "status": "pending_otp",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    sent = False
    if payload.delivery_method == "sms" and payload.phone:
        try:
            from core_app.core.config import get_settings
            settings = get_settings()
            cfg = TelnyxConfig(api_key=settings.telnyx_api_key, messaging_profile_id=settings.telnyx_messaging_profile_id or None)
            send_sms(cfg=cfg, to=payload.phone, body=f"Your FusionEMS authorization code: {otp_code}. Expires in {OTP_EXPIRY_MINUTES} min.")
            sent = True
        except TelnyxNotConfigured:
            pass

    if (not sent) and payload.email:
        try:
            get_ses_service().send_otp(email=payload.email, otp_code=otp_code, expires_minutes=OTP_EXPIRY_MINUTES)
            sent = True
        except Exception:
            pass

    return {
        "session_id": str(session_id),
        "delivery_method": payload.delivery_method,
        "otp_sent": sent,
        "expires_in_minutes": OTP_EXPIRY_MINUTES,
    }


@router.post("/verify-otp")
async def verify_otp(
    payload: OtpVerifyRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    matches = svc.repo("auth_rep_sessions").list_raw_by_field("session_id", str(payload.session_id), limit=1)
    session = matches[0] if matches else None

    if not session:
        raise HTTPException(status_code=404, detail="session_not_found")

    data = session["data"]
    if data.get("status") != "pending_otp":
        raise HTTPException(status_code=400, detail="session_not_pending")

    expires_at = datetime.fromisoformat(data["otp_expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="otp_expired")

    MAX_OTP_ATTEMPTS = 5
    attempts = int(data.get("attempts", 0))
    if attempts >= MAX_OTP_ATTEMPTS:
        raise HTTPException(status_code=429, detail="otp_max_attempts_exceeded")

    submitted_hash = hashlib.sha256(payload.otp_code.encode()).hexdigest()
    if not hmac.compare_digest(data.get("otp_hash", ""), submitted_hash):
        await svc.update(
            table="auth_rep_sessions",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            record_id=uuid.UUID(str(session["id"])),
            expected_version=session["version"],
            patch={"attempts": attempts + 1},
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        raise HTTPException(status_code=400, detail="invalid_otp")

    await svc.update(
        table="auth_rep_sessions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(session["id"])),
        expected_version=session["version"],
        patch={"status": "verified", "verified_at": datetime.now(timezone.utc).isoformat()},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    rep_row = await svc.create(
        table="authorized_reps",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "patient_account_id": data["patient_account_id"],
            "relationship": data["relationship"],
            "full_name": data["full_name"],
            "email": data.get("email"),
            "phone": data.get("phone"),
            "verification_method": data.get("delivery_method", "otp"),
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    await emit_authorization_verified(
        publisher=publisher,
        tenant_id=current.tenant_id,
        rep_id=uuid.UUID(rep_row["id"]),
        patient_id=uuid.UUID(data["patient_account_id"]),
        method="otp",
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    return {"status": "verified", "authorized_rep_id": rep_row["id"]}


@router.post("/upload-document")
async def upload_rep_document(
    payload: RepDocumentUploadRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    matches = svc.repo("auth_rep_sessions").list_raw_by_field("session_id", str(payload.session_id), limit=1)
    session = matches[0] if matches else None
    if not session:
        raise HTTPException(status_code=404, detail="session_not_found")
    if session["data"].get("status") not in ("verified", "active"):
        raise HTTPException(status_code=400, detail="rep_not_verified")

    doc_row = await svc.create(
        table="rep_documents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "session_id": str(payload.session_id),
            "document_type": payload.document_type,
            "s3_key": payload.s3_key,
            "notes": payload.notes,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"document_id": doc_row["id"], "status": "uploaded"}


@router.get("/reps")
async def list_reps(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    reps = svc.repo("authorized_reps").list(tenant_id=current.tenant_id, limit=500)
    return {"reps": reps}
