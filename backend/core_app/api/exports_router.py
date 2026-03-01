from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/exports", tags=["Exports"])


@router.post("/tenant")
async def export_tenant(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    job = await svc.create(
        table="export_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"type": "tenant_export", "status": "queued"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return job


@router.get("/{job_id}")
async def export_status(
    job_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rec = svc.repo("export_jobs").get(tenant_id=current.tenant_id, record_id=job_id)
    return rec or {"error": "not_found"}
