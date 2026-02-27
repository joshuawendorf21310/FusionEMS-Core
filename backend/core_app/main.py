from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
from core_app.middleware.rate_limiter import TenantRateLimitMiddleware
from core_app.middleware.tenant_context import TenantContextMiddleware
from core_app.observability.otel import configure_otel

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")

from core_app.api.cad_calls_router import router as cad_calls_router
from core_app.api.cad_units_router import router as cad_units_router
from core_app.api.mdt_router import router as mdt_router
from core_app.api.crewlink_router import router as crewlink_router
from core_app.api.transportlink_router import router as transportlink_router
from core_app.api.scheduling_router import router as scheduling_router
from core_app.api.fleet_router import router as fleet_router
from core_app.api.weather_router import router as weather_router
from core_app.api.documents_router import router as documents_router
from core_app.api.signatures_router import router as signatures_router
from core_app.api.fax_router import router as fax_router
from core_app.api.billing_router import router as billing_router
from core_app.api.pricing_router import router as pricing_router
from core_app.api.imports_router import router as imports_router
from core_app.api.exports_router import router as exports_router
from core_app.api.icd10_router import router as icd10_router
from core_app.api.fire_ops_router import router as fire_ops_router
from core_app.api.fire_epcr_router import router as fire_epcr_router
from core_app.api.fire_statements_router import router as fire_statements_router
from core_app.api.founder_router import router as founder_router
from core_app.api.metrics_router import router as metrics_router
from core_app.api.ai_router import router as ai_router
from core_app.api.fhir_router import router as fhir_router
from core_app.api.accreditation_router import router as accreditation_router
from core_app.api.onboarding_router import router as onboarding_router
from core_app.api.roi_router import router as roi_router
from core_app.api.auth_rep_router import router as auth_rep_router
from core_app.api.tracking_router import router as tracking_router
from core_app.api.lob_router import router as lob_router
from core_app.api.lob_webhook_router import router as lob_webhook_router
from core_app.api.stripe_webhook_router import router as stripe_webhook_router
from core_app.api.statements_router import router as statements_router
from core_app.api.voice_webhook_router import router as voice_webhook_router
from core_app.api.sms_webhook_router import router as sms_webhook_router
from core_app.api.fax_webhook_router import router as fax_webhook_router
from core_app.api.payments_router import router as payments_router
from core_app.api.visibility_router import router as visibility_router
from core_app.api.nemsis_manager_router import router as nemsis_manager_router
from core_app.api.template_router import router as template_router
from core_app.api.billing_command_router import router as billing_command_router
from core_app.api.roi_funnel_router import router as roi_funnel_router
from core_app.api.mobile_ops_router import router as mobile_ops_router
from core_app.api.system_health_router import router as system_health_router
from core_app.api.export_status_router import router as export_status_router

app = FastAPI(title=settings.app_name)
configure_otel(app)

_allowed_origins = [
    f"https://{settings.root_domain_name}" if hasattr(settings, "root_domain_name") else "https://fusionemsquantum.com",
    "https://app.fusionemsquantum.com",
    "https://api.fusionemsquantum.com",
]
if settings.debug:
    _allowed_origins.extend(["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID", "X-Correlation-ID", "X-Request-ID"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Correlation-ID"],
    max_age=600,
)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(TenantRateLimitMiddleware)


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
app.include_router(cad_calls_router)
app.include_router(cad_units_router)
app.include_router(mdt_router)
app.include_router(crewlink_router)
app.include_router(transportlink_router)
app.include_router(scheduling_router)
app.include_router(fleet_router)
app.include_router(weather_router)
app.include_router(documents_router)
app.include_router(signatures_router)
app.include_router(fax_router)
app.include_router(billing_router)
app.include_router(pricing_router)
app.include_router(imports_router)
app.include_router(exports_router)
app.include_router(icd10_router)
app.include_router(fire_ops_router)
app.include_router(fire_epcr_router)
app.include_router(fire_statements_router)
app.include_router(founder_router)
app.include_router(roi_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(accreditation_router, prefix="/api/v1")
app.include_router(fhir_router, prefix="/api/v1")
app.include_router(metrics_router)
app.include_router(ai_router)
app.include_router(auth_rep_router)
app.include_router(tracking_router)
app.include_router(lob_router)
app.include_router(lob_webhook_router)
app.include_router(stripe_webhook_router)
app.include_router(statements_router)
app.include_router(voice_webhook_router)
app.include_router(sms_webhook_router)
app.include_router(fax_webhook_router)
app.include_router(payments_router, prefix="/api/v1")
app.include_router(template_router)
app.include_router(billing_command_router)
app.include_router(roi_funnel_router)
app.include_router(mobile_ops_router)
app.include_router(system_health_router)
app.include_router(export_status_router)
app.include_router(visibility_router, prefix="/api/v1")
app.include_router(nemsis_manager_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
