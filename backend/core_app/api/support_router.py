from __future__ import annotations

import json as _json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.support.chat_service import ChatService

router = APIRouter(prefix="/api/v1/support", tags=["Support Chat"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _chat(db: Session, tenant_id: str, user_id: str) -> ChatService:
    return ChatService(db, get_event_publisher(), tenant_id, user_id)


@router.post("/threads")
async def create_thread(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _chat(db, str(current.tenant_id), str(current.user_id))
    return svc.create_thread(
        thread_type=payload.get("thread_type", "general"),
        title=payload.get("title", ""),
        claim_id=payload.get("claim_id"),
    )


@router.get("/threads")
async def list_threads(
    status: str = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    params: dict[str, Any] = {
        "tenant_id": str(current.tenant_id),
        "user_id": str(current.user_id),
    }
    status_clause = ""
    if status:
        status_clause = "AND data->>'status' = :status AND data->>'created_by' = :user_id "
        params["status"] = status
    rows = (
        db.execute(
            text(
                f"SELECT id, tenant_id, data, version, created_at, updated_at "
                f"FROM support_threads "
                f"WHERE tenant_id = :tenant_id AND deleted_at IS NULL "
                f"AND data->>'created_by' = :user_id "
                f"{status_clause}"
                f"ORDER BY created_at DESC LIMIT 100"
            ),
            params,
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    row = (
        db.execute(
            text(
                "SELECT id, tenant_id, data, version, created_at, updated_at "
                "FROM support_threads "
                "WHERE id = :id AND tenant_id = :tenant_id AND deleted_at IS NULL"
            ),
            {"id": thread_id, "tenant_id": str(current.tenant_id)},
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")

    svc = _chat(db, str(current.tenant_id), str(current.user_id))
    messages = svc.get_thread_messages(thread_id)
    return {"thread": dict(row), "messages": messages}


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    thread = (
        db.execute(
            text(
                "SELECT id FROM support_threads "
                "WHERE id = :id AND tenant_id = :tenant_id AND deleted_at IS NULL"
            ),
            {"id": thread_id, "tenant_id": str(current.tenant_id)},
        )
        .mappings()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    svc = _chat(db, str(current.tenant_id), str(current.user_id))
    return svc.send_message(
        thread_id=thread_id,
        content=payload.get("content", ""),
        attachments=payload.get("attachments"),
        sender_role="agency",
    )


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    thread = (
        db.execute(
            text(
                "SELECT id FROM support_threads "
                "WHERE id = :id AND tenant_id = :tenant_id AND deleted_at IS NULL"
            ),
            {"id": thread_id, "tenant_id": str(current.tenant_id)},
        )
        .mappings()
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    svc = _chat(db, str(current.tenant_id), str(current.user_id))
    return svc.get_thread_messages(thread_id)


@router.get("/inbox")
async def founder_inbox(
    unread: bool = Query(default=False),
    escalated: bool = Query(default=False),
    claim_linked: bool = Query(default=False),
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    clauses = ["deleted_at IS NULL"]
    params: dict[str, Any] = {}

    if unread:
        clauses.append("(data->>'unread_founder')::boolean = true")
    if escalated:
        clauses.append("(data->>'escalated')::boolean = true")
    if claim_linked:
        clauses.append("data->>'claim_id' IS NOT NULL")

    where = "WHERE " + " AND ".join(clauses)
    rows = (
        db.execute(
            text(
                f"SELECT id, tenant_id, data, version, created_at, updated_at "
                f"FROM support_threads "
                f"{where} "
                f"ORDER BY "
                f"  (data->>'escalated')::boolean DESC, "
                f"  (data->>'unread_founder')::boolean DESC, "
                f"  created_at DESC "
                f"LIMIT 200"
            ),
            params,
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


@router.get("/inbox/{thread_id}")
async def founder_get_thread(
    thread_id: str,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    row = (
        db.execute(
            text(
                "SELECT id, tenant_id, data, version, created_at, updated_at "
                "FROM support_threads "
                "WHERE id = :id AND deleted_at IS NULL"
            ),
            {"id": thread_id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread_data = dict(row)
    tenant_id = str(thread_data["tenant_id"])

    rows_m = (
        db.execute(
            text(
                "SELECT id, tenant_id, data, version, created_at, updated_at "
                "FROM support_messages "
                "WHERE data->>'thread_id' = :thread_id AND deleted_at IS NULL "
                "ORDER BY created_at ASC"
            ),
            {"thread_id": thread_id},
        )
        .mappings()
        .all()
    )
    messages = [dict(r) for r in rows_m]

    ai_summary = thread_data.get("data", {}).get("ai_summary")
    if not ai_summary:
        svc = _chat(db, tenant_id, str(current.user_id))
        ai_summary = svc.generate_thread_summary(thread_id)

    return {"thread": thread_data, "messages": messages, "ai_summary": ai_summary}


@router.post("/inbox/{thread_id}/reply")
async def founder_reply(
    thread_id: str,
    payload: dict[str, Any],
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    row = (
        db.execute(
            text("SELECT tenant_id FROM support_threads WHERE id = :id AND deleted_at IS NULL"),
            {"id": thread_id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")

    tenant_id = str(row["tenant_id"])
    svc = _chat(db, tenant_id, str(current.user_id))
    msg = svc.send_message(
        thread_id=thread_id,
        content=payload.get("content", ""),
        attachments=payload.get("attachments"),
        sender_role="founder",
    )
    svc.mark_thread_read_by_founder(thread_id)
    return msg


@router.post("/inbox/{thread_id}/resolve")
async def founder_resolve(
    thread_id: str,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    result = (
        db.execute(
            text(
                "UPDATE support_threads "
                "SET data = data || CAST(:patch AS jsonb), updated_at = now() "
                "WHERE id = :id AND deleted_at IS NULL "
                "RETURNING id"
            ),
            {
                "id": thread_id,
                "patch": _json.dumps(
                    {"status": "resolved", "resolved_at": datetime.now(UTC).isoformat()},
                    separators=(",", ":"),
                ),
            },
        )
        .mappings()
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Thread not found")
    db.commit()
    return {"thread_id": thread_id, "status": "resolved"}


@router.post("/inbox/{thread_id}/summarize")
async def founder_summarize(
    thread_id: str,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    row = (
        db.execute(
            text("SELECT tenant_id FROM support_threads WHERE id = :id AND deleted_at IS NULL"),
            {"id": thread_id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")

    tenant_id = str(row["tenant_id"])
    svc = _chat(db, tenant_id, str(current.user_id))
    summary = svc.generate_thread_summary(thread_id)

    db.execute(
        text(
            "UPDATE support_threads "
            "SET data = data || CAST(:patch AS jsonb), updated_at = now() "
            "WHERE id = :id"
        ),
        {
            "id": thread_id,
            "patch": _json.dumps({"ai_summary": summary}, separators=(",", ":")),
        },
    )
    db.commit()
    return {"thread_id": thread_id, "ai_summary": summary}
