from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

PHI_PROTECTED_PREFIXES = [
    "/api/v1/patients",
    "/api/v1/incidents",
    "/api/v1/vitals",
    "/api/v1/epcr",
    "/api/v1/billing",
    "/api/v1/claims",
    "/api/v1/fhir",
    "/api/v1/documents",
    "/api/v1/statements",
    "/api/v1/exports",
    "/api/v1/nemsis",
]

PUBLIC_PREFIXES = [
    "/public/",
    "/api/v1/auth/",
    "/api/v1/health",
    "/health",
    "/webhooks/",
    "/realtime/",
]


class PHILockMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        for pub in PUBLIC_PREFIXES:
            if path.startswith(pub):
                return await call_next(request)

        is_phi = any(path.startswith(p) for p in PHI_PROTECTED_PREFIXES)
        if not is_phi:
            return await call_next(request)

        tenant_status = getattr(request.state, "tenant_status", None)
        legal_status = getattr(request.state, "tenant_legal_status", None)

        if tenant_status in (None, "provisioning", "restricted", "failed"):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "phi_locked",
                    "message": "PHI access is locked. Complete legal signing and payment to unlock patient data.",
                    "next_step": "complete_onboarding",
                },
            )

        if legal_status not in (None, "signed", "active"):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "phi_locked",
                    "message": "BAA must be signed before accessing patient data.",
                    "next_step": "sign_baa",
                },
            )

        return await call_next(request)
