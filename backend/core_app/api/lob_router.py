from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.integrations.lob_service import LobNotConfigured, _get_lob_config
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1", tags=["LOB Mail"])


@router.post("/billing/statements/{case_id}/mail/html")
async def send_html_statement_letter(
    case_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Legacy HTML-based Lob letter endpoint (kept for backwards compatibility).
    For production billing statements use POST /api/v1/statements/{statement_id}/mail
    which generates a branded PDF with audit footer.
    """
    import requests as _requests

    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    try:
        cfg = _get_lob_config()
    except LobNotConfigured:
        raise HTTPException(status_code=503, detail="lob_not_configured")

    to_addr = payload.get("to_address")
    from_addr = payload.get("from_address")
    html_content = payload.get("html", "")
    if not html_content or not html_content.strip():
        raise HTTPException(status_code=400, detail="html field is required and must not be empty")

    if not to_addr or not from_addr:
        raise HTTPException(status_code=400, detail="to_address and from_address required")

    try:
        resp = _requests.post(
            "https://api.lob.com/v1/letters",
            auth=(cfg.api_key, ""),
            json={
                "description": f"FusionEMS Statement - Case {case_id}",
                "to": to_addr,
                "from": from_addr,
                "file": html_content,
                "color": False,
                "double_sided": False,
                "mail_type": "usps_first_class",
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"lob_error: {exc}")

    lob_id = result.get("id")
    row = await svc.create(
        table="lob_letters",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "case_id": str(case_id),
            "lob_id": lob_id,
            "status": "created",
            "lob_response": result,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    await publisher.publish(
        event_name="letter.sent",
        tenant_id=current.tenant_id,
        entity_id=uuid.UUID(row["id"]),
        payload={"lob_id": lob_id, "case_id": str(case_id)},
        entity_type="lob_letter",
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "queued", "lob_id": lob_id, "letter_id": row["id"]}
