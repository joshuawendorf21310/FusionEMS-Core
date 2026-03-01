from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

RATE_LIMITS: dict[str, dict[str, int]] = {
    "api_calls_per_minute": {"starter": 60, "professional": 300, "enterprise": 1000, "founder": 9999},
    "exports_per_day": {"starter": 10, "professional": 100, "enterprise": 500, "founder": 9999},
    "ai_calls_per_hour": {"starter": 20, "professional": 100, "enterprise": 500, "founder": 9999},
}

IP_RATE_LIMIT = 200
WINDOW_SECONDS = 60

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis as redis_lib

            from core_app.core.config import get_settings
            settings = get_settings()
            _redis_client = redis_lib.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                ssl_cert_reqs=None,
            )
        except Exception as e:
            logger.warning("Redis rate limiter init failed: %s", e)
            return None
    return _redis_client


def _redis_sliding_window(key: str, limit: int, window: int) -> tuple[bool, int]:
    """Sliding window counter using Redis. Returns (allowed, remaining)."""
    r = _get_redis()
    if r is None:
        return True, limit

    now = time.time()
    window_start = now - window

    try:
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window + 5)
        results = pipe.execute()
        count = int(results[2])
        remaining = max(0, limit - count)
        return count <= limit, remaining
    except Exception as e:
        logger.warning("Redis rate limit check failed: %s — allowing request", e)
        return True, limit


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_paths: list[str] | None = None) -> None:
        super().__init__(app)
        self.excluded_paths = set(excluded_paths or [
            "/health", "/api/v1/health", "/healthz",
            "/api/v1/webhooks", "/api/v1/public", "/track",
        ])

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        path = request.url.path

        if any(path.startswith(ep) for ep in self.excluded_paths):
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", None)

        if not tenant_id:
            # Rate limit unauthenticated requests by IP
            ip = (request.client.host if request.client else "unknown") or "unknown"
            key = f"rate:ip:{ip}:minute"
            allowed, remaining = _redis_sliding_window(key, IP_RATE_LIMIT, WINDOW_SECONDS)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"error": "rate_limit_exceeded", "message": "Too many requests from this IP."},
                    headers={"X-RateLimit-Limit": str(IP_RATE_LIMIT), "X-RateLimit-Remaining": "0", "Retry-After": "60"},
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(IP_RATE_LIMIT)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        tenant = getattr(request.state, "tenant", None)
        tier = "starter"
        if tenant and hasattr(tenant, "billing_tier"):
            tier = tenant.billing_tier or "starter"

        limit = RATE_LIMITS["api_calls_per_minute"].get(tier, 60)
        key = f"rate:api:{tenant_id}:minute"
        allowed, remaining = _redis_sliding_window(key, limit, WINDOW_SECONDS)

        if not allowed:
            logger.warning("Rate limit exceeded for tenant %s (tier=%s)", tenant_id, tier)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"API rate limit exceeded. Limit: {limit} requests/minute.",
                    "upgrade_url": "/billing/upgrade",
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
