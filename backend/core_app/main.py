from fastapi import FastAPI

from core_app.api.audit_router import router as audit_router
from core_app.api.auth_router import router as auth_router
from core_app.core.config import get_settings
from core_app.core.logging import configure_logging
from core_app.middleware.audit_logging import AuditLoggingMiddleware
from core_app.middleware.tenant_context import TenantContextMiddleware

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")

app = FastAPI(title=settings.app_name)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(TenantContextMiddleware)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
