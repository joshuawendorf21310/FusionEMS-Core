from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt

from core_app.api.dependencies import get_current_user
from core_app.core.config import get_settings
from core_app.schemas.auth import CurrentUser
from core_app.services.cognito_jwt import CognitoAuthError, verify_cognito_jwt

import redis.asyncio as redis_async

router = APIRouter(prefix="/realtime", tags=["realtime"])


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _presence_ping(r, tenant_id: str, kind: str, key: str) -> None:
    # Presence keys with TTL allow CAD/MDT/Crewlink dashboards to show online status.
    presence_key = f"tenant.{tenant_id}.presence.{kind}.{key}"
    await r.set(presence_key, "1", ex=45)


@router.get("/sse")
async def realtime_sse(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    patterns: list[str] = Query(default=[]),
) -> StreamingResponse:
    """Tenant-scoped Server-Sent Events stream with Redis pub/sub fanout.

    - Default subscription: psubscribe `tenant.<tenant_id>.*`
    - Optional patterns can be provided (must be subset of tenant.<id>.*)
    """
    settings = get_settings()
    r = redis_async.from_url(settings.redis_url, decode_responses=True)
    tenant_id = str(current.tenant_id)

    safe_patterns: list[str] = []
    if patterns:
        for p in patterns:
            if not p.startswith(f"tenant.{tenant_id}."):
                continue
            safe_patterns.append(p)
    if not safe_patterns:
        safe_patterns = [f"tenant.{tenant_id}.*"]

    pubsub = r.pubsub()
    await pubsub.psubscribe(*safe_patterns)

    async def event_stream() -> AsyncIterator[str]:
        yield _sse({"eventType": "connected", "tenantId": tenant_id, "ts": datetime.now(timezone.utc).isoformat()})
        last_heartbeat = 0.0

        try:
            while True:
                if await request.is_disconnected():
                    break

                # heartbeat every 15s
                now = time.time()
                if now - last_heartbeat > 15:
                    last_heartbeat = now
                    await _presence_ping(r, tenant_id, "user", str(current.user_id))
                    yield _sse({"eventType": "heartbeat", "ts": datetime.now(timezone.utc).isoformat()})

                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") in ("pmessage", "message"):
                    raw = message.get("data")
                    try:
                        payload = json.loads(raw) if isinstance(raw, str) else raw
                    except Exception:
                        payload = {"eventType": "raw", "data": raw}
                    yield _sse(payload)

                await asyncio.sleep(0.01)
        finally:
            await pubsub.close()
            await r.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.websocket("/ws")
async def realtime_ws(websocket: WebSocket) -> None:
    """Primary realtime channel (tenant-scoped) via WebSocket.

    Auth: `token` query parameter (JWT).
    Client may send: {"type":"subscribe","patterns":[...]}.
    """
    settings = get_settings()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return

    try:
        if settings.auth_mode.lower() == "cognito":
            claims = verify_cognito_jwt(token)
            tenant_id = claims.tenant_id
            user_id = claims.sub
        else:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            tenant_id = payload.get("tenant_id")
            user_id = payload.get("sub")
            if not tenant_id or not user_id:
                raise JWTError("missing claims")
    except (JWTError, CognitoAuthError):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    r = redis_async.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()

    tenant_id_str = str(tenant_id)
    patterns = [f"tenant.{tenant_id_str}.*"]
    await pubsub.psubscribe(*patterns)
    await _presence_ping(r, tenant_id_str, "user", str(user_id))

    async def sender() -> None:
        last_ping = 0.0
        while True:
            now = time.time()
            if now - last_ping > 20:
                last_ping = now
                await _presence_ping(r, tenant_id_str, "user", str(user_id))
                await websocket.send_text(json.dumps({"eventType": "heartbeat", "ts": datetime.now(timezone.utc).isoformat()}))

            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "pmessage":
                raw = msg.get("data")
                await websocket.send_text(raw if isinstance(raw, str) else json.dumps(raw))
            await asyncio.sleep(0.01)

    async def receiver() -> None:
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
            except Exception:
                continue
            if obj.get("type") == "subscribe":
                req_patterns = obj.get("patterns") or []
                safe = []
                for p in req_patterns:
                    if isinstance(p, str) and p.startswith(f"tenant.{tenant_id_str}."):
                        safe.append(p)
                if safe:
                    await pubsub.punsubscribe()
                    await pubsub.psubscribe(*safe)

    send_task = asyncio.create_task(sender())
    recv_task = asyncio.create_task(receiver())
    try:
        await asyncio.gather(send_task, recv_task)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        send_task.cancel()
        recv_task.cancel()
        await pubsub.close()
        await r.close()
