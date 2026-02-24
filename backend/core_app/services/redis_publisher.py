from __future__ import annotations

import json
import uuid
from typing import Any

from core_app.services.event_publisher import EventPublisher


class RedisPublisher(EventPublisher):
    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis

        self.client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def publish(
        self,
        event_name: str,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        message = {
            "event_name": event_name,
            "tenant_id": str(tenant_id),
            "entity_id": str(entity_id),
            "payload": payload,
        }
        await self.client.publish("events", json.dumps(message))
