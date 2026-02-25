from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from core_app.core.config import get_settings

try:
    from redis.asyncio import Redis as AsyncRedis
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    AsyncRedis = None  # type: ignore
    redis_async = None  # type: ignore


class EventPublisher(ABC):
    @abstractmethod
    async def publish(
        self,
        event_name: str,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        entity_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        raise NotImplementedError


class NoOpEventPublisher(EventPublisher):
    async def publish(
        self,
        event_name: str,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        entity_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:  # noqa: ARG002
        return None


class RedisEventPublisher(EventPublisher):
    """Publish tenant-scoped JSON envelopes to Redis pub/sub.

    Envelope contract:
      {topic, tenant_id, entity_type, entity_id, event_type, payload, ts, correlation_id}
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._redis_url = settings.redis_url
        self._client: AsyncRedis | None = None

    async def _get_client(self) -> AsyncRedis:
        if self._client is None:
            if redis_async is None:
                raise RuntimeError("redis.asyncio is not available")
            self._client = redis_async.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def publish(
        self,
        event_name: str,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        entity_type: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        topic = f"tenant.{tenant_id}.{event_name}"
        envelope = {
            "topic": topic,
            "tenant_id": str(tenant_id),
            "entity_type": entity_type or "unknown",
            "entity_id": str(entity_id),
            "event_type": event_name,
            "payload": payload,
            "ts": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
        }
        client = await self._get_client()
        await client.publish(topic, json.dumps(envelope))


def get_event_publisher(db_session=None) -> EventPublisher:
    """Factory: returns RedisEventPublisher when REDIS_URL is configured, otherwise NoOp."""
    settings = get_settings()
    if getattr(settings, "redis_url", None) and redis_async is not None:
        return RedisEventPublisher(settings.redis_url)
    return NoOpEventPublisher()
