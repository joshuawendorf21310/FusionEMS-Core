from fastapi import Request
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = None
        request.state.tenant_status = None
        request.state.tenant_legal_status = None

        response = await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is not None:
            response.headers["x-tenant-id"] = str(tenant_id)

            if request.state.tenant_status is None:
                try:
                    from core_app.db.session import get_db_session

                    db = next(get_db_session())
                    row = (
                        db.execute(
                            text(
                                "SELECT data->>'status' AS status, data->>'legal_status' AS legal_status "
                                "FROM tenants WHERE tenant_id = :tid AND deleted_at IS NULL LIMIT 1"
                            ),
                            {"tid": str(tenant_id)},
                        )
                        .mappings()
                        .first()
                    )
                    if row:
                        request.state.tenant_status = row["status"]
                        request.state.tenant_legal_status = row["legal_status"]
                    db.close()
                except Exception:
                    pass

        return response
