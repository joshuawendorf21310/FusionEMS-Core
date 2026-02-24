import re
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from core_app.core.config import get_settings
from core_app.realtime.websocket_manager import WebSocketManager

router = APIRouter(tags=["realtime"])
manager = WebSocketManager()
CHANNEL_PATTERN = re.compile(r"^(incident|claim):([0-9a-fA-F-]{36}):([0-9a-fA-F-]{36})$")


def _extract_token(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if token:
        return token
    auth = websocket.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    settings = get_settings()
    token = _extract_token(websocket)
    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        tenant_id = UUID(payload["tenant_id"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("action") != "subscribe":
                await websocket.send_json({"error": "unsupported_action"})
                continue

            channel = str(message.get("channel", ""))
            match = CHANNEL_PATTERN.match(channel)
            if not match:
                await websocket.send_json({"error": "invalid_channel"})
                continue

            channel_tenant_id = UUID(match.group(2))
            if channel_tenant_id != tenant_id:
                await websocket.send_json({"error": "forbidden_channel"})
                continue

            manager.subscribe(channel=channel, websocket=websocket)
            await websocket.send_json({"status": "subscribed", "channel": channel})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
