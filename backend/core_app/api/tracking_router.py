from __future__ import annotations

import contextlib
import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.realtime_events import emit_letter_viewed

router = APIRouter(tags=["Tracking"])

TRACKING_PIXEL = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


def generate_track_token(entity_id: str, tenant_id: str, entity_type: str = "letter") -> str:
    raw = f"{entity_id}:{tenant_id}:{entity_type}:{secrets.token_hex(8)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


@router.get("/track/{token}")
async def track_view(
    token: str,
    request: Request,
    db: Session = Depends(db_session_dependency),
):
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    track_events = svc.repo("track_tokens").list_raw_by_field("token", token, limit=1)

    if track_events:
        track = track_events[0]
        data = track.get("data", {})

        expires_at_raw = data.get("expires_at")
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
                if datetime.now(UTC) > expires_at:
                    return Response(content=TRACKING_PIXEL, media_type="image/gif")
            except Exception:
                pass

        entity_type = data.get("entity_type", "letter")
        entity_id_raw = data.get("entity_id")
        tenant_id_raw = data.get("tenant_id")
        tenant_uuid = uuid.UUID(tenant_id_raw) if tenant_id_raw else uuid.UUID(int=0)

        await svc.create(
            table="track_events",
            tenant_id=tenant_uuid,
            actor_user_id=None,
            data={
                "token": token,
                "entity_type": entity_type,
                "entity_id": entity_id_raw,
                "ip": ip,
                "user_agent": ua[:512],
                "viewed_at": datetime.now(UTC).isoformat(),
            },
            correlation_id=None,
        )

        with contextlib.suppress(Exception):
            await svc.update(
                table="track_tokens",
                tenant_id=tenant_uuid,
                actor_user_id=None,
                record_id=uuid.UUID(str(track["id"])),
                expected_version=track.get("version", 1),
                patch={
                    "last_viewed_at": datetime.now(UTC).isoformat(),
                    "view_count": (data.get("view_count", 0) + 1),
                },
                correlation_id=None,
            )

        if entity_type == "letter" and entity_id_raw and tenant_id_raw:
            await emit_letter_viewed(
                publisher=publisher,
                tenant_id=uuid.UUID(tenant_id_raw),
                letter_id=uuid.UUID(entity_id_raw),
                view_token=token,
            )

        redirect_url = data.get("redirect_url")
        if redirect_url:
            return RedirectResponse(url=redirect_url, status_code=302)

    return Response(content=TRACKING_PIXEL, media_type="image/gif")


@router.post("/api/v1/tracking/tokens")
async def create_track_token(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    entity_id = str(payload.get("entity_id", uuid.uuid4()))
    tenant_id = str(payload.get("tenant_id", uuid.uuid4()))
    entity_type = payload.get("entity_type", "letter")
    redirect_url = payload.get("redirect_url")

    token = generate_track_token(entity_id, tenant_id, entity_type)
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    await svc.create(
        table="track_tokens",
        tenant_id=uuid.UUID(tenant_id),
        actor_user_id=None,
        data={
            "token": token,
            "entity_id": entity_id,
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "redirect_url": redirect_url,
            "created_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=None,
    )
    return {"token": token, "track_url": f"/track/{token}"}
