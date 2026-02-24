from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int
    details: dict[str, Any] | None = None

    def to_response(self, trace_id: str | None) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details or {},
                "trace_id": trace_id,
            }
        }


class ErrorCodes:
    INCIDENT_NOT_FOUND = "INCIDENT_NOT_FOUND"
    INCIDENT_CONFLICT = "INCIDENT_CONFLICT"
    CONCURRENCY_CONFLICT = "CONCURRENCY_CONFLICT"
    INCIDENT_NUMBER_CONFLICT = "INCIDENT_NUMBER_CONFLICT"
    INCIDENT_INVALID_TRANSITION = "INCIDENT_INVALID_TRANSITION"
    INCIDENT_FORBIDDEN_TRANSITION = "INCIDENT_FORBIDDEN_TRANSITION"
    TENANT_SCOPE_REQUIRED = "TENANT_SCOPE_REQUIRED"
    PATIENT_NOT_FOUND = "PATIENT_NOT_FOUND"
    PATIENT_CONFLICT = "PATIENT_CONFLICT"
    PATIENT_INCIDENT_MISMATCH = "PATIENT_INCIDENT_MISMATCH"
