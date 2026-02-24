from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core_app.api.audit_router import router as audit_router
from core_app.api.auth_router import router as auth_router
from core_app.api.incident_router import router as incident_router
from core_app.api.patient_router import router as patient_router
from core_app.api.vital_router import router as vital_router
from core_app.api.health_router import router as health_router
from core_app.api.realtime_router import router as realtime_router
from core_app.api.nemsis_router import router as nemsis_router
from core_app.api.neris_router import router as neris_router
from core_app.core.config import get_settings
from core_app.core.errors import AppError
from core_app.core.logging import configure_logging
from core_app.middleware.audit_logging import AuditLoggingMiddleware
from core_app.middleware.tenant_context import TenantContextMiddleware

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")

app = FastAPI(title=settings.app_name)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(TenantContextMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    trace_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(status_code=exc.status_code, content=exc.to_response(trace_id=trace_id))


app.include_router(auth_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(incident_router, prefix="/api/v1")
app.include_router(patient_router, prefix="/api/v1")
app.include_router(vital_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(realtime_router, prefix="/api/v1")
app.include_router(nemsis_router, prefix="/api/v1")
app.include_router(neris_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
