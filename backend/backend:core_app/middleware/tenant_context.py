from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Tenant identity is established by authenticated dependencies from JWT claims,
        # never from caller-provided headers.
        request.state.tenant_id = None
        response = await call_next(request)
        if request.state.tenant_id is not None:
            response.headers["x-tenant-id"] = str(request.state.tenant_id)
        return response
