from __future__ import annotations
import json as _json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


async def emit_platform_event(
    db,
    tenant_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
    idempotency_key: str = None,
) -> dict:
    if idempotency_key:
        existing = db.execute(
            text(
                "SELECT id FROM platform_events "
                "WHERE tenant_id = :tenant_id AND data->>'idempotency_key' = :ikey "
                "LIMIT 1"
            ),
            {"tenant_id": tenant_id, "ikey": idempotency_key},
        ).mappings().first()
        if existing:
            return {"event_id": str(existing["id"]), "created": False}

    data = {
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
        "read": False,
    }
    if idempotency_key:
        data["idempotency_key"] = idempotency_key

    row = db.execute(
        text(
            "INSERT INTO platform_events (tenant_id, data) "
            "VALUES (:tenant_id, CAST(:data AS jsonb)) "
            "RETURNING id, created_at"
        ),
        {"tenant_id": tenant_id, "data": _json.dumps(data, separators=(",", ":"))},
    ).mappings().one()
    db.commit()
    return {"event_id": str(row["id"]), "created": True}


@router.get("/feed")
async def get_events_feed(
    cursor: str = Query(default=None),
    limit: int = Query(default=50, le=200),
    event_types: list[str] = Query(default=[]),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    params: dict[str, Any] = {
        "tenant_id": str(current.tenant_id),
        "cursor": cursor,
        "types": event_types if event_types else None,
        "limit": limit,
    }
    rows = db.execute(
        text(
            "SELECT id, tenant_id, data, created_at "
            "FROM platform_events "
            "WHERE tenant_id = :tenant_id "
            "  AND (:cursor IS NULL OR created_at > :cursor::timestamptz) "
            "  AND (:types IS NULL OR data->>'event_type' = ANY(:types)) "
            "ORDER BY created_at ASC "
            "LIMIT :limit"
        ),
        params,
    ).mappings().all()

    events = []
    for r in rows:
        d = dict(r.get("data", {}))
        events.append({
            "event_id": str(r["id"]),
            "event_type": d.get("event_type"),
            "entity_type": d.get("entity_type"),
            "entity_id": d.get("entity_id"),
            "payload": d.get("payload", {}),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "read": d.get("read", False),
        })

    next_cursor = events[-1]["created_at"] if events else None
    has_more = len(events) == limit
    return {"events": events, "next_cursor": next_cursor, "has_more": has_more, "count": len(events)}


@router.post("/publish")
async def publish_event(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    result = await emit_platform_event(
        db,
        tenant_id=str(current.tenant_id),
        event_type=payload.get("event_type", ""),
        entity_type=payload.get("entity_type", ""),
        entity_id=payload.get("entity_id", ""),
        payload=payload.get("payload", {}),
    )
    return result


@router.post("/{event_id}/read")
async def mark_event_read(
    event_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    db.execute(
        text(
            "INSERT INTO event_reads (tenant_id, data) "
            "VALUES (:tenant_id, CAST(:data AS jsonb)) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "tenant_id": str(current.tenant_id),
            "data": _json.dumps(
                {
                    "event_id": event_id,
                    "user_id": str(current.user_id),
                    "read_at": datetime.now(timezone.utc).isoformat(),
                },
                separators=(",", ":"),
            ),
        },
    )
    db.commit()
    return {"event_id": event_id, "read": True}


@router.get("/unread-count")
async def unread_count(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    row = db.execute(
        text(
            "SELECT COUNT(*) AS cnt FROM platform_events pe "
            "WHERE pe.tenant_id = :tenant_id "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM event_reads er "
            "    WHERE er.data->>'event_id' = pe.id::text "
            "      AND er.data->>'user_id' = :user_id"
            "  )"
        ),
        {"tenant_id": str(current.tenant_id), "user_id": str(current.user_id)},
    ).mappings().one()
    return {"count": row["cnt"]}


@router.post("/internal/emit")
async def internal_emit(
    payload: dict[str, Any],
    db: Session = Depends(db_session_dependency),
    x_internal_secret: str = Header(default=""),
):
    _expected = os.environ.get("INTERNAL_WORKER_SECRET", "")
    if not _expected or x_internal_secret != _expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")

    result = await emit_platform_event(
        db,
        tenant_id=str(tenant_id),
        event_type=payload.get("event_type", ""),
        entity_type=payload.get("entity_type", ""),
        entity_id=payload.get("entity_id", ""),
        payload=payload.get("payload", {}),
        idempotency_key=payload.get("idempotency_key"),
    )
    return result
