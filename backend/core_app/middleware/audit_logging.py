import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.audit_context = {
            "actor_user_id": None,
            "tenant_id": None,
            "correlation_id": request.state.correlation_id,
        }
        response = await call_next(request)
        response.headers["x-correlation-id"] = request.state.correlation_id
        return response
