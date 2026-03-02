from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status")
def status(db: Session = Depends(db_session_dependency)) -> dict:
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception:
        checks["database"] = "unreachable"

    redis_ok = False
    if settings.redis_url:
        try:
            import redis

            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            checks["redis"] = "connected"
            redis_ok = True
        except Exception:
            checks["redis"] = "unreachable"
    else:
        checks["redis"] = "not_configured"

    checks["auth_mode"] = settings.auth_mode
    checks["version"] = "quantum-v1"

    all_ok = checks["database"] == "connected" and (redis_ok or not settings.redis_url)
    checks["system_status"] = "operational" if all_ok else "degraded"

    return checks
