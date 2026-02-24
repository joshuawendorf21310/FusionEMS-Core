import json
from typing import Iterator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from core_app.api.dependencies import get_current_user
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/realtime", tags=["realtime"])

def sse_format(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"

@router.get("/sse")
def realtime_sse(request: Request, user: CurrentUser = Depends(get_current_user)) -> StreamingResponse:
    # NOTE: This is a minimal placeholder that streams a heartbeat.
    # Codex must extend: Redis pub/sub fan-out per tenant_id and authorization filtering.
    def gen() -> Iterator[str]:
        yield sse_format({"eventType":"connected","tenantId":str(user.tenant_id)})
        while True:
            if request.client is None:
                break
            yield sse_format({"eventType":"heartbeat"})
            import time
            time.sleep(15)
    return StreamingResponse(gen(), media_type="text/event-stream")
