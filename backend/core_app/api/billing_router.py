from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.billing.validation import BillingValidator
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/billing", tags=['Billing'])


@router.post("/cases/{case_id}/validate")
async def validate(case_id: uuid.UUID, request: Request, current: CurrentUser = Depends(get_current_user), db: Session = Depends(db_session_dependency)):
    require_role(current, ["founder","billing","admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    validator = BillingValidator(db, tenant_id=current.tenant_id)
    try:
        result = validator.validate_case(case_id)
    except ValueError:
        return {"error": "billing_case_not_found", "case_id": str(case_id)}

    missing = result["missing_docs"]
    # Create missing-doc tasks (idempotent by (case_id, doc_type) via lookup)
    created_tasks: list[dict[str, Any]] = []
    existing = svc.repo("missing_document_tasks").list(current.tenant_id, limit=5000)
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
        "created_tasks": [t["id"] for t in created_tasks],
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