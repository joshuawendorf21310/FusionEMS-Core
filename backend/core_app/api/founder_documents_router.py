from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role
from core_app.core.config import get_settings
from core_app.schemas.auth import CurrentUser
from core_app.services.event_publisher import get_event_publisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/founder/documents", tags=["Founder Documents"])

LEGAL_TEMPLATES = [
    {
        "doc_type": "BAA",
        "template_version": "1.0",
        "description": "HIPAA Business Associate Agreement — covers permitted uses, safeguards, breach notification, subcontractors, PHI return/destroy, and HHS availability.",
        "required": True,
    },
    {
        "doc_type": "MSA",
        "template_version": "1.0",
        "description": "Master Subscription Agreement — covers parties, subscription scope, support SLAs, fees, customer responsibilities, AI disclaimer, confidentiality, IP, warranties, liability cap, term/termination, data export, and governing law.",
        "required": True,
    },
    {
        "doc_type": "ORDER_FORM",
        "template_version": "1.0",
        "description": "Order Form — captures agency details, selected modules, call volume tier, monthly base fee, and per-claim trigger definition.",
        "required": True,
    },
]


@router.get("/legal-templates")
async def list_legal_templates(
    current: CurrentUser = Depends(require_role("founder")),
):
    return {"templates": LEGAL_TEMPLATES}


@router.get("/executed-documents")
async def list_executed_documents(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    settings = get_settings()
    rows = (
        db.execute(
            text(
                """
            SELECT ld.id, ld.tenant_id, ld.data AS doc_data, ld.created_at,
                   lp.data AS packet_data
            FROM legal_documents ld
            JOIN legal_packets lp ON lp.id = (ld.data->>'packet_id')::uuid
            WHERE ld.data->>'status' = 'executed'
            ORDER BY ld.created_at DESC
            """
            )
        )
        .mappings()
        .all()
    )

    results = []
    for row in rows:
        doc_data = dict(row["doc_data"] or {})
        s3_key = doc_data.get("s3_key_executed")
        presigned_url = None
        if s3_key and settings.s3_bucket_docs:
            try:
                from core_app.documents.s3_storage import presign_get

                presigned_url = presign_get(
                    bucket=settings.s3_bucket_docs, key=s3_key, expires_seconds=300
                )
            except Exception as exc:
                logger.warning("Could not generate presigned URL for %s: %s", s3_key, exc)
        results.append(
            {
                "id": str(row["id"]),
                "doc_data": doc_data,
                "packet_data": dict(row["packet_data"] or {}),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "presigned_url": presigned_url,
            }
        )

    return {"documents": results, "total": len(results)}


@router.get("/executed-documents/{doc_id}/download")
async def download_executed_document(
    doc_id: str,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    settings = get_settings()
    row = (
        db.execute(
            text("SELECT id, data FROM legal_documents WHERE id = :doc_id LIMIT 1"),
            {"doc_id": doc_id},
        )
        .mappings()
        .first()
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_data = dict(row["data"] or {})
    s3_key = doc_data.get("s3_key_executed")
    if not s3_key:
        raise HTTPException(status_code=404, detail="Executed PDF not available")

    if not settings.s3_bucket_docs:
        raise HTTPException(status_code=503, detail="S3 not configured")

    try:
        from core_app.documents.s3_storage import presign_get

        url = presign_get(bucket=settings.s3_bucket_docs, key=s3_key, expires_seconds=300)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 error: {str(exc)}")

    return {"doc_id": doc_id, "presigned_url": url, "expires_seconds": 300}


@router.get("/onboarding-applications")
async def list_onboarding_applications(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    rows = (
        db.execute(
            text(
                """
            SELECT oa.id, oa.contact_email, oa.agency_name, oa.agency_type,
                   oa.annual_call_volume, oa.selected_modules,
                   oa.status, oa.legal_status, oa.tenant_id,
                   oa.stripe_customer_id, oa.stripe_subscription_id,
                   oa.provisioned_at, oa.created_at,
                   lp.id AS packet_id, lp.data AS packet_data
            FROM onboarding_applications oa
            LEFT JOIN legal_packets lp ON (lp.data->>'application_id') = oa.id::text
            ORDER BY oa.created_at DESC
            """
            )
        )
        .mappings()
        .all()
    )

    pipeline_order = [
        "started",
        "legal_pending",
        "legal_signed",
        "payment_pending",
        "provisioned",
        "active",
    ]

    results = []
    for row in rows:
        results.append(
            {
                "application_id": str(row["id"]),
                "contact_email": row["contact_email"],
                "agency_name": row["agency_name"],
                "agency_type": row["agency_type"],
                "annual_call_volume": row["annual_call_volume"],
                "selected_modules": row["selected_modules"],
                "status": row["status"],
                "legal_status": row["legal_status"],
                "tenant_id": str(row["tenant_id"]) if row["tenant_id"] else None,
                "stripe_customer_id": row["stripe_customer_id"],
                "stripe_subscription_id": row["stripe_subscription_id"],
                "provisioned_at": row["provisioned_at"].isoformat()
                if row["provisioned_at"]
                else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "packet_id": str(row["packet_id"]) if row["packet_id"] else None,
                "packet_data": dict(row["packet_data"] or {}) if row["packet_data"] else None,
                "pipeline_stage": row["status"],
            }
        )

    return {"applications": results, "total": len(results), "pipeline_order": pipeline_order}


@router.post("/onboarding-applications/{application_id}/resend-legal")
async def resend_legal(
    application_id: str,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    app_row = (
        db.execute(
            text("SELECT id, status FROM onboarding_applications WHERE id = :app_id"),
            {"app_id": application_id},
        )
        .mappings()
        .first()
    )
    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    db.execute(
        text(
            "UPDATE onboarding_applications SET status = 'legal_pending', legal_status = 'pending' WHERE id = :app_id"
        ),
        {"app_id": application_id},
    )
    db.commit()

    from core_app.onboarding.legal_service import LegalService

    svc = LegalService(db, get_event_publisher())
    legal_status = svc.get_legal_status(application_id)

    return {
        "application_id": application_id,
        "status": "legal_pending",
        "packet_id": legal_status.get("packet_id"),
        "message": "Application reset to legal_pending. Existing packet retained for resending.",
    }


@router.post("/onboarding-applications/{application_id}/resend-checkout")
async def resend_checkout(
    application_id: str,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    settings = get_settings()
    app_row = (
        db.execute(
            text(
                "SELECT id, agency_name, annual_call_volume, selected_modules, legal_status "
                "FROM onboarding_applications WHERE id = :app_id"
            ),
            {"app_id": application_id},
        )
        .mappings()
        .first()
    )
    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app_row["legal_status"] != "signed":
        raise HTTPException(
            status_code=422, detail="Legal documents must be signed before checkout"
        )

    if not settings.stripe_secret_key:
        return {
            "checkout_url": None,
            "status": "stripe_not_configured",
            "note": "Contact Stripe configuration to complete setup",
        }

    try:
        import stripe as stripe_lib

        stripe_lib.api_key = settings.stripe_secret_key
        selected_modules = app_row["selected_modules"] or []
        annual_call_volume = int(app_row["annual_call_volume"] or 0)

        base_amount_cents = 50000
        if annual_call_volume > 5000:
            base_amount_cents = 150000
        elif annual_call_volume > 2000:
            base_amount_cents = 100000

        module_amount_cents = len(selected_modules) * 5000
        base_url = settings.api_base_url.rstrip("/")

        session = stripe_lib.checkout.Session.create(
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"FusionEMS Quantum — {app_row['agency_name']}",
                            "description": f"Platform subscription — {annual_call_volume} annual calls",
                        },
                        "unit_amount": base_amount_cents + module_amount_cents,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }
            ],
            metadata={"application_id": application_id, "source": "onboarding_resend"},
            success_url=f"{base_url}/onboarding/success?application_id={application_id}",
            cancel_url=f"{base_url}/onboarding/cancel?application_id={application_id}",
        )
        return {"checkout_url": session.url, "application_id": application_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(exc)}")


@router.post("/onboarding-applications/{application_id}/manual-provision")
async def manual_provision(
    application_id: str,
    payload: dict,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    if not payload.get("confirm"):
        raise HTTPException(
            status_code=422, detail="confirm: true is required to manually trigger provisioning"
        )

    app_row = (
        db.execute(
            text(
                "SELECT id, agency_name, contact_email, agency_type, annual_call_volume, "
                "selected_modules, legal_status, status FROM onboarding_applications WHERE id = :app_id"
            ),
            {"app_id": application_id},
        )
        .mappings()
        .first()
    )
    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app_row["legal_status"] != "signed":
        raise HTTPException(
            status_code=422, detail="Legal documents must be signed before provisioning"
        )

    from core_app.services.tenant_provisioning import provision_tenant_from_application

    try:
        result = await provision_tenant_from_application(
            db,
            application_id,
            dict(app_row),
            {"type": "manual_provision", "source": "founder_override"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {str(exc)}")

    now = datetime.now(UTC).isoformat()
    db.execute(
        text(
            "UPDATE onboarding_applications SET status = 'provisioned', "
            "provisioned_at = :now, tenant_id = :tid WHERE id = :app_id"
        ),
        {"now": now, "tid": result.get("tenant_id"), "app_id": application_id},
    )
    db.commit()

    return {
        "application_id": application_id,
        "provisioned": True,
        "tenant_id": result.get("tenant_id"),
        "status": result.get("status"),
    }


@router.post("/onboarding-applications/{application_id}/revoke")
async def revoke_application(
    application_id: str,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    app_row = (
        db.execute(
            text("SELECT id, tenant_id FROM onboarding_applications WHERE id = :app_id"),
            {"app_id": application_id},
        )
        .mappings()
        .first()
    )
    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    db.execute(
        text("UPDATE onboarding_applications SET status = 'revoked' WHERE id = :app_id"),
        {"app_id": application_id},
    )

    if app_row["tenant_id"]:
        db.execute(
            text(
                "UPDATE tenants SET data = jsonb_set(data, '{status}', '\"restricted\"') "
                "WHERE tenant_id = :tid"
            ),
            {"tid": str(app_row["tenant_id"])},
        )

    db.commit()
    return {
        "application_id": application_id,
        "status": "revoked",
        "tenant_restricted": app_row["tenant_id"] is not None,
    }


@router.get("/sign-events")
async def list_sign_events(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    sign_events = (
        db.execute(
            text(
                """
            SELECT id, tenant_id, data, created_at
            FROM legal_sign_events
            ORDER BY created_at DESC
            LIMIT 500
            """
            )
        )
        .mappings()
        .all()
    )

    doc_events = (
        db.execute(
            text(
                """
            SELECT id, tenant_id, data, created_at
            FROM document_events
            ORDER BY created_at DESC
            LIMIT 500
            """
            )
        )
        .mappings()
        .all()
    )

    combined = []
    for row in sign_events:
        combined.append(
            {
                "event_category": "sign_event",
                "id": str(row["id"]),
                "data": dict(row["data"] or {}),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        )
    for row in doc_events:
        combined.append(
            {
                "event_category": "document_event",
                "id": str(row["id"]),
                "data": dict(row["data"] or {}),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        )

    combined.sort(key=lambda x: x["created_at"] or "", reverse=True)

    return {"events": combined, "total": len(combined)}
