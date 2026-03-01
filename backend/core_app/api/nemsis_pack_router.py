from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.nemsis.pack_manager import PackManager
from core_app.schemas.auth import CurrentUser
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/nemsis/packs", tags=["NEMSIS Packs"])


def _manager(db: Session, current: CurrentUser) -> PackManager:
    return PackManager(db, get_event_publisher(), current.tenant_id, current.user_id)


@router.post("/")
async def create_pack(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    manager = _manager(db, current)
    return await manager.create_pack(
        pack_name=payload["pack_name"],
        description=payload.get("description", ""),
        nemsis_version=payload.get("nemsis_version", "3.5.1"),
        state_code=payload.get("state_code", "NATIONAL"),
        pack_type=payload["pack_type"],
        notes=payload.get("notes", ""),
    )


@router.get("/active")
async def get_active_pack(
    state_code: str = Query(...),
    pack_type: str = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    manager = _manager(db, current)
    pack = manager.get_active_pack(state_code, pack_type)
    if pack is None:
        raise HTTPException(status_code=404, detail="No active pack found")
    return pack


@router.get("/")
async def list_packs(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _manager(db, current).list_packs()


@router.get("/{pack_id}")
async def get_pack(
    pack_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    pack = _manager(db, current).get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")
    return pack


@router.get("/{pack_id}/completeness")
async def get_pack_completeness(
    pack_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _manager(db, current).get_pack_completeness(pack_id)


@router.get("/{pack_id}/files")
async def list_pack_files(
    pack_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _manager(db, current).list_pack_files(pack_id)


@router.post("/{pack_id}/files/upload")
async def upload_file(
    pack_id: str,
    request: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    content = await file.read()
    correlation_id = getattr(request.state, "correlation_id", None)
    return await _manager(db, current).ingest_file(
        pack_id=pack_id,
        filename=file.filename or "upload",
        content=content,
        correlation_id=correlation_id,
    )


@router.post("/{pack_id}/activate")
async def activate_pack(
    pack_id: str,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    correlation_id = getattr(request.state, "correlation_id", None)
    result = await _manager(db, current).activate_pack(
        pack_id=pack_id,
        actor_user_id=str(current.user_id),
        correlation_id=correlation_id,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict or pack not found")
    return result


@router.post("/{pack_id}/stage")
async def stage_pack(
    pack_id: str,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    correlation_id = getattr(request.state, "correlation_id", None)
    result = await _manager(db, current).stage_pack(pack_id=pack_id, correlation_id=correlation_id)
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict or pack not found")
    return result


@router.post("/{pack_id}/archive")
async def archive_pack(
    pack_id: str,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    correlation_id = getattr(request.state, "correlation_id", None)
    result = await _manager(db, current).archive_pack(
        pack_id=pack_id, correlation_id=correlation_id
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict or pack not found")
    return result
