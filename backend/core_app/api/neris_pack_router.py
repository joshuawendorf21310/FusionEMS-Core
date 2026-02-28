from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role
from core_app.neris.pack_manager import NERISPackManager
from core_app.neris.validator import NERISValidator
from core_app.schemas.auth import CurrentUser
from core_app.services.event_publisher import get_event_publisher
from core_app.core.config import get_settings

router = APIRouter(prefix="/api/v1/founder/neris", tags=["NERIS Packs"])


def _manager(db: Session, current: CurrentUser) -> NERISPackManager:
    return NERISPackManager(db, get_event_publisher(), current.tenant_id, current.user_id)


def _validator(db: Session, current: CurrentUser) -> NERISValidator:
    return NERISValidator(db, get_event_publisher(), current.tenant_id)


def _enqueue_pack_compile(pack_id: str, tenant_id: str, actor_user_id: str) -> None:
    import json
    import boto3
    queue_url = get_settings().neris_pack_compile_queue_url
    if not queue_url:
        return
    import logging as _logging
    _log = _logging.getLogger(__name__)
    try:
        boto3.client("sqs").send_message(
            QueueUrl=queue_url,
            MessageGroupId=pack_id,
            MessageDeduplicationId=f"compile-{pack_id}",
            MessageBody=json.dumps({"job_type": "neris.pack.compile_rules", "pack_id": pack_id, "tenant_id": tenant_id, "actor_user_id": actor_user_id}),
        )
    except Exception as exc:
        _log.error("neris_pack_compile_enqueue_failed pack_id=%s error=%s", pack_id, exc)


@router.post("/packs/import")
async def import_pack(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    payload.get("source_type", "github")
    repo = payload.get("repo", "ulfsri/neris-framework")
    ref = payload.get("ref", "main")
    name = payload.get("name", "")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    correlation_id = getattr(request.state, "correlation_id", None)
    return await _manager(db, current).import_from_github(repo=repo, ref=ref, name=name, correlation_id=correlation_id)


@router.post("/packs/{pack_id}/activate")
async def activate_pack(
    pack_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        result = await _manager(db, current).activate_pack(pack_id=pack_id, correlation_id=correlation_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict or pack not found")
    return result


@router.get("/packs")
async def list_packs(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _manager(db, current).list_packs()


@router.get("/packs/{pack_id}")
async def get_pack(
    pack_id: uuid.UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    mgr = _manager(db, current)
    pack = mgr.get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")
    files = mgr.svc.repo("neris_pack_files").list(tenant_id=current.tenant_id, limit=500)
    pack_files = [f for f in files if (f.get("data") or {}).get("pack_id") == str(pack_id)]
    return {"pack": pack, "files": pack_files}


@router.post("/packs/{pack_id}/compile")
async def compile_pack(
    pack_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    mgr = _manager(db, current)
    pack = mgr.get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")
    _enqueue_pack_compile(str(pack_id), str(current.tenant_id), str(current.user_id))
    return {"queued": True, "pack_id": str(pack_id)}


@router.post("/validate/bundle")
async def validate_bundle(
    payload: dict[str, Any],
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    pack_id_str = payload.get("pack_id")
    entity_type = payload.get("entity_type", "INCIDENT")
    data = payload.get("payload", {})
    if not pack_id_str:
        raise HTTPException(status_code=422, detail="pack_id is required")
    try:
        pack_id = uuid.UUID(pack_id_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="pack_id must be a valid UUID")
    issues = _validator(db, current).validate(pack_id=pack_id, entity_type=entity_type, payload=data)
    return {"valid": len([i for i in issues if i.get("severity") == "error"]) == 0, "issues": issues}
