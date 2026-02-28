from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.onboarding.legal_service import LegalService
from core_app.roi.engine import compute_roi, hash_outputs
from core_app.services.event_publisher import get_event_publisher

try:
    import stripe as stripe_lib
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/onboarding", tags=["Onboarding"])


def _legal_svc(db: Session) -> LegalService:
    return LegalService(db, get_event_publisher())


@router.post("/start")
async def onboarding_start(payload: dict[str, Any], db: Session = Depends(db_session_dependency)):
    email = str(payload.get("email", "")).lower().strip()
    agency_name = str(payload.get("agency_name", "")).strip()
    agency_type = str(payload.get("agency_type", "EMS"))
    zip_code = str(payload.get("zip_code", ""))
    annual_call_volume = int(payload.get("annual_call_volume", 0))
    current_billing_percent = float(payload.get("current_billing_percent", 0.0))
    payer_mix = payload.get("payer_mix", {})
    level_mix = payload.get("level_mix", {})
    selected_modules = payload.get("selected_modules", [])

    if not email or not agency_name:
        raise HTTPException(status_code=422, detail="email and agency_name are required")
    if agency_type not in ("EMS", "Fire", "HEMS"):
        raise HTTPException(status_code=422, detail="agency_type must be EMS, Fire, or HEMS")

    roi = compute_roi({
        "zip_code": zip_code,
        "annual_call_volume": annual_call_volume,
        "service_type": agency_type,
        "current_billing_percent": current_billing_percent,
        "payer_mix": payer_mix,
        "level_mix": level_mix,
        "selected_modules": selected_modules,
    })
    roi_hash = hash_outputs(roi)

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    existing = db.execute(
        text(
            "SELECT id, roi_snapshot_hash, status FROM onboarding_applications "
            "WHERE contact_email = :email AND agency_name = :agency AND status = 'started' "
            "AND created_at >= :cutoff LIMIT 1"
        ),
        {"email": email, "agency": agency_name, "cutoff": cutoff},
    ).mappings().first()

    if existing:
        return {
            "application_id": str(existing["id"]),
            "roi_snapshot_hash": existing["roi_snapshot_hash"],
            "status": existing["status"],
            "next_steps": ["sign_legal", "checkout", "provisioning"],
        }

    row = db.execute(
        text(
            """
            INSERT INTO onboarding_applications (
                contact_email, agency_name, zip_code, agency_type, annual_call_volume,
                current_billing_percent, payer_mix, level_mix, selected_modules,
                roi_snapshot_hash, status, legal_status
            ) VALUES (
                :email, :agency, :zip, :atype, :vol, :pct,
                :payer::jsonb, :level::jsonb, :mods::jsonb,
                :h, 'started', 'pending'
            ) RETURNING id
            """
        ),
        {
            "email": email,
            "agency": agency_name,
            "zip": zip_code,
            "atype": agency_type,
            "vol": annual_call_volume,
            "pct": current_billing_percent,
            "payer": json.dumps(payer_mix),
            "level": json.dumps(level_mix),
            "mods": json.dumps(selected_modules),
            "h": roi_hash,
        },
    ).mappings().first()
    db.commit()

    return {
        "application_id": str(row["id"]),
        "roi_snapshot_hash": roi_hash,
        "status": "started",
        "next_steps": ["sign_legal", "checkout", "provisioning"],
    }


@router.post("/legal/packet/create")
async def legal_packet_create(payload: dict[str, Any], db: Session = Depends(db_session_dependency)):
    application_id = str(payload.get("application_id", "")).strip()
    signer_name = str(payload.get("signer_name", "")).strip()
    signer_email = str(payload.get("signer_email", "")).strip()
    str(payload.get("signer_title", "")).strip()

    if not application_id:
        raise HTTPException(status_code=422, detail="application_id is required")

    app_row = db.execute(
        text(
            "SELECT id, agency_name, agency_type, annual_call_volume, selected_modules, "
            "current_billing_percent, status, legal_status FROM onboarding_applications WHERE id = :app_id"
        ),
        {"app_id": application_id},
    ).mappings().first()

    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app_row["status"] not in ("started", "legal_pending"):
        raise HTTPException(status_code=422, detail=f"Application status '{app_row['status']}' does not allow legal packet creation")

    svc = _legal_svc(db)
    existing_status = svc.get_legal_status(application_id)
    if existing_status["packet_id"]:
        packet = svc.get_packet(existing_status["packet_id"], application_id)
        if packet:
            return packet

    plan_data = {
        "agency_name": app_row["agency_name"],
        "agency_type": app_row["agency_type"],
        "annual_call_volume": app_row["annual_call_volume"],
        "selected_modules": app_row["selected_modules"] if app_row["selected_modules"] else [],
        "current_billing_percent": app_row["current_billing_percent"],
    }

    packet = svc.create_packet(
        application_id=application_id,
        signer_email=signer_email,
        signer_name=signer_name,
        agency_name=app_row["agency_name"],
        plan_data=plan_data,
    )

    db.execute(
        text("UPDATE onboarding_applications SET status = 'legal_pending' WHERE id = :app_id"),
        {"app_id": application_id},
    )
    db.commit()

    return packet


@router.get("/legal/packet/{packet_id}")
async def legal_packet_get(
    packet_id: str,
    application_id: str,
    db: Session = Depends(db_session_dependency),
):
    svc = _legal_svc(db)
    packet = svc.get_packet(packet_id, application_id)
    if packet is None:
        raise HTTPException(status_code=404, detail="Packet not found")
    return packet


@router.post("/legal/packet/{packet_id}/sign")
async def legal_packet_sign(
    packet_id: str,
    payload: dict[str, Any],
    db: Session = Depends(db_session_dependency),
):
    application_id = str(payload.get("application_id", "")).strip()
    if not application_id:
        raise HTTPException(status_code=422, detail="application_id is required")

    svc = _legal_svc(db)
    packet = svc.get_packet(packet_id, application_id)
    if packet is None:
        raise HTTPException(status_code=404, detail="Packet not found or application_id mismatch")

    signing_data = {
        "signer_name": payload.get("signer_name", ""),
        "signer_email": payload.get("signer_email", ""),
        "signer_title": payload.get("signer_title", ""),
        "ip_address": payload.get("ip_address", ""),
        "user_agent": payload.get("user_agent", ""),
        "consents": payload.get("consents", {}),
        "signature_text": payload.get("signature_text", ""),
    }

    try:
        updated = svc.sign_packet(packet_id, signing_data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    db.execute(
        text("UPDATE onboarding_applications SET legal_status = 'signed' WHERE id = :app_id"),
        {"app_id": application_id},
    )
    db.commit()

    documents_summary = [
        {
            "doc_type": d.get("data", {}).get("doc_type"),
            "s3_key_executed": d.get("data", {}).get("s3_key_executed"),
            "sha256": d.get("data", {}).get("sha256"),
        }
        for d in updated.get("documents", [])
    ]

    return {"signed": True, "packet_id": packet_id, "documents": documents_summary}


@router.post("/checkout/start")
async def checkout_start(payload: dict[str, Any], db: Session = Depends(db_session_dependency)):
    application_id = str(payload.get("application_id", "")).strip()
    if not application_id:
        raise HTTPException(status_code=422, detail="application_id is required")

    app_row = db.execute(
        text(
            "SELECT id, agency_name, annual_call_volume, selected_modules, legal_status, status "
            "FROM onboarding_applications WHERE id = :app_id"
        ),
        {"app_id": application_id},
    ).mappings().first()

    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app_row["legal_status"] != "signed":
        raise HTTPException(status_code=422, detail="Legal documents must be signed before payment")

    settings = get_settings()

    if not STRIPE_AVAILABLE or not settings.stripe_secret_key:
        db.execute(
            text("UPDATE onboarding_applications SET status = 'payment_pending' WHERE id = :app_id"),
            {"app_id": application_id},
        )
        db.commit()
        return {
            "checkout_url": None,
            "status": "stripe_not_configured",
            "note": "Contact sales to complete setup",
        }

    try:
        stripe_lib.api_key = settings.stripe_secret_key
        selected_modules = app_row["selected_modules"] or []
        annual_call_volume = int(app_row["annual_call_volume"] or 0)

        base_amount_cents = 50000
        if annual_call_volume > 5000:
            base_amount_cents = 150000
        elif annual_call_volume > 2000:
            base_amount_cents = 100000

        module_amount_cents = len(selected_modules) * 5000

        line_items = [
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"FusionEMS Quantum — {app_row['agency_name']}",
                        "description": f"Platform subscription setup — {annual_call_volume} annual calls, "
                                       f"{len(selected_modules)} modules",
                    },
                    "unit_amount": base_amount_cents + module_amount_cents,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }
        ]

        base_url = settings.api_base_url.rstrip("/")
        session = stripe_lib.checkout.Session.create(
            mode="subscription",
            line_items=line_items,
            metadata={"application_id": application_id, "source": "onboarding"},
            success_url=f"{base_url}/onboarding/success?application_id={application_id}",
            cancel_url=f"{base_url}/onboarding/cancel?application_id={application_id}",
        )

        db.execute(
            text("UPDATE onboarding_applications SET status = 'payment_pending' WHERE id = :app_id"),
            {"app_id": application_id},
        )
        db.commit()

        return {"checkout_url": session.url}

    except Exception as exc:
        logger.error("Stripe checkout creation failed for application %s: %s", application_id, exc)
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(exc)}")


@router.get("/status/{application_id}")
async def onboarding_status(application_id: str, db: Session = Depends(db_session_dependency)):
    app_row = db.execute(
        text(
            "SELECT id, status, legal_status, tenant_id, provisioned_at "
            "FROM onboarding_applications WHERE id = :app_id"
        ),
        {"app_id": application_id},
    ).mappings().first()

    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    status = app_row["status"]
    legal_status = app_row["legal_status"]
    provisioned = app_row["provisioned_at"] is not None
    tenant_id = str(app_row["tenant_id"]) if app_row["tenant_id"] else None

    next_step_map = {
        "started": "sign_legal",
        "legal_pending": "sign_legal",
        "payment_pending": "complete_payment",
        "provisioned": "access_platform",
        "active": "access_platform",
        "revoked": "contact_support",
    }
    next_step = next_step_map.get(status, "contact_support")
    if status == "legal_pending" and legal_status == "signed":
        next_step = "complete_payment"

    return {
        "application_id": application_id,
        "status": status,
        "legal_status": legal_status,
        "provisioned": provisioned,
        "tenant_id": tenant_id,
        "next_step": next_step,
    }
