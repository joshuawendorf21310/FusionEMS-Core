from collections import defaultdict
from typing import DefaultDict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._channels: DefaultDict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def disconnect(self, websocket: WebSocket) -> None:
        for channel in list(self._channels.keys()):
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                self._channels.pop(channel, None)

    def subscribe(self, *, channel: str, websocket: WebSocket) -> None:
        self._channels[channel].add(websocket)

    async def broadcast(self, *, channel: str, message: dict) -> None:
        for ws in list(self._channels.get(channel, set())):
            await ws.send_json(message)
