from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from core_app.core.config import get_settings

try:
    import redis.asyncio as redis_async
except Exception:
    redis_async = None

logger = logging.getLogger(__name__)


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

    def publish_sync(
        self,
        *,
        topic: str | None = None,
        event_name: str | None = None,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID | str | None = None,
        entity_type: str | None = None,
        event_type: str | None = None,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        import asyncio
        name = event_name or event_type or (topic.split(".")[-1] if topic else "event")
        eid = entity_id if isinstance(entity_id, uuid.UUID) else uuid.uuid4()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.publish(name, tenant_id, eid, payload, entity_type=entity_type, correlation_id=correlation_id))
            else:
                loop.run_until_complete(self.publish(name, tenant_id, eid, payload, entity_type=entity_type, correlation_id=correlation_id))
        except Exception as exc:
            logger.error(
                "event_publisher.publish_sync failed",
                extra={
                    "event_name": name,
                    "tenant_id": str(tenant_id),
                    "entity_id": str(eid),
                    "correlation_id": correlation_id,
                    "error": str(exc),
                },
                exc_info=exc,
            )


class NoOpEventPublisher(EventPublisher):
    async def publish(self, event_name, tenant_id, entity_id, payload, *, entity_type=None, correlation_id=None):
        logger.warning(
            "event_publisher.noop: event dropped — no publisher configured",
            extra={
                "event_name": event_name,
                "tenant_id": str(tenant_id),
                "entity_id": str(entity_id),
                "correlation_id": correlation_id,
            },
        )


class RedisEventPublisher(EventPublisher):
    def __init__(self) -> None:
        settings = get_settings()
        self._redis_url = settings.redis_url
        self._client = None

    async def _get_client(self):
        if self._client is None:
            if redis_async is None:
                raise RuntimeError("redis.asyncio not available")
            self._client = redis_async.from_url(
                self._redis_url,
                decode_responses=True,
                ssl_cert_reqs=None,
            )
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
            "ts": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id,
        }
        try:
            client = await self._get_client()
            await client.publish(topic, json.dumps(envelope))
        except Exception as exc:
            logger.error(
                "event_publisher.redis.publish failed",
                extra={
                    "event_name": event_name,
                    "topic": topic,
                    "tenant_id": str(tenant_id),
                    "entity_id": str(entity_id),
                    "correlation_id": correlation_id,
                    "error": str(exc),
                },
                exc_info=exc,
            )


_publisher_instance: EventPublisher | None = None


def get_event_publisher(db_session=None) -> EventPublisher:
    global _publisher_instance
    if _publisher_instance is None:
        settings = get_settings()
        if getattr(settings, "redis_url", None) and redis_async is not None:
            _publisher_instance = RedisEventPublisher()
        else:
            logger.critical(
                "event_publisher.fallback: Redis unavailable or not configured — "
                "using NoOpEventPublisher; all events will be dropped. "
                "Set REDIS_URL to enable real-time event streaming.",
                extra={"redis_url_set": bool(getattr(settings, "redis_url", None))},
            )
            _publisher_instance = NoOpEventPublisher()
    return _publisher_instance
