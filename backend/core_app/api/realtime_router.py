from __future__ import annotations

import json
import time
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])

@router.get("/sse")
async def sse(request: Request):
    # Minimal SSE stream: heartbeat + server time.
    # Event payload must never include PHI; IDs only.
    async def gen():
        while True:
            if await request.is_disconnected():
                break
            payload = {"eventType": "heartbeat", "timestamp": datetime.utcnow().isoformat() + "Z"}
            yield f"event: heartbeat\ndata: {json.dumps(payload)}\n\n"
            time.sleep(10)
    return StreamingResponse(gen(), media_type="text/event-stream")
