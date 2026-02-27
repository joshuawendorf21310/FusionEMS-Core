from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.neris.copilot import NERISCopilot
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/v1/neris/copilot", tags=["NERIS Copilot"])

ALLOWED_ROLES = {"agency_admin", "founder", "admin", "ems"}


def _check_role(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/explain")
async def explain_issues(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check_role(current)
    issues = payload.get("issues", [])
    if not isinstance(issues, list):
        raise HTTPException(status_code=422, detail="issues must be a list")
    context = payload.get("context") or {}
    copilot = NERISCopilot()
    return copilot.explain_issues(issues=issues, context=context)
