from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_DELAYS_SECONDS = [5, 15, 60, 300, 900]


async def enqueue_webhook(
    *,
    svc,
    tenant_id: uuid.UUID | None,
    webhook_type: str,
    payload: dict[str, Any],
) -> str:
    """Persist a webhook to the DLQ table for background processing."""
    row = await svc.create(
        table="webhook_dlq",
        tenant_id=tenant_id or uuid.UUID(int=0),
        actor_user_id=None,
        data={
            "webhook_type": webhook_type,
            "payload": payload,
            "attempts": 0,
            "status": "pending",
            "next_retry_at": datetime.now(timezone.utc).isoformat(),
        },
        correlation_id=None,
    )
    return str(row.get("id", ""))


async def process_webhook_with_retry(
    handler: Callable[[dict[str, Any]], Awaitable[Any]],
    payload: dict[str, Any],
    event_id: str,
    source: str,
    db,
    svc,
) -> dict[str, Any]:
    """Process a webhook inline for immediate delivery (used in router context).

    On failure, enqueues to DLQ for background retry rather than sleeping inline.
    """
    try:
        result = await handler(payload)
        return {"status": "ok", "attempts": 1}
    except Exception as e:
        logger.warning("Webhook delivery failed for %s %s: %s — enqueuing DLQ", source, event_id, e)
        try:
            tenant_id = uuid.UUID(payload.get("tenant_id", "")) if payload.get("tenant_id") else uuid.UUID(int=0)
            next_retry = datetime.now(timezone.utc) + timedelta(seconds=RETRY_DELAYS_SECONDS[0])
            await svc.create(
                table="webhook_dlq",
                tenant_id=tenant_id,
                actor_user_id=None,
                data={
                    "event_id": event_id,
                    "source": source,
                    "webhook_type": source,
                    "payload": payload,
                    "error": str(e),
                    "attempts": 1,
                    "status": "pending",
                    "next_retry_at": next_retry.isoformat(),
                },
                correlation_id=None,
            )
        except Exception as dlq_err:
            logger.error("Failed to enqueue DLQ for %s %s: %s", source, event_id, dlq_err)
        return {"status": "enqueued_for_retry", "event_id": event_id}


async def process_dlq_batch(
    handlers: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]],
    svc,
    tenant_id: uuid.UUID,
    batch_size: int = 50,
) -> int:
    """Process pending DLQ items. Called from background worker."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    processed = 0

    try:
        pending = svc.repo("webhook_dlq").list(tenant_id=tenant_id, limit=batch_size)
    except Exception as e:
        logger.error("Failed to fetch DLQ batch: %s", e)
        return 0

    for item in pending:
        data = item.get("data", {})
        if data.get("status") not in ("pending", "retrying"):
            continue

        next_retry_raw = data.get("next_retry_at")
        if next_retry_raw:
            try:
                next_retry = datetime.fromisoformat(str(next_retry_raw).replace("Z", "+00:00"))
                if now < next_retry:
                    continue
            except Exception:
                pass

        attempts = int(data.get("attempts", 0))
        webhook_type = data.get("webhook_type", data.get("source", ""))
        handler = handlers.get(webhook_type)

        if not handler:
            logger.warning("No handler for DLQ webhook_type=%s", webhook_type)
            continue

        try:
            await handler(data.get("payload", {}))
            await svc.update(
                table="webhook_dlq",
                tenant_id=tenant_id,
                actor_user_id=None,
                record_id=uuid.UUID(str(item["id"])),
                expected_version=item.get("version", 1),
                patch={"status": "processed", "attempts": attempts + 1, "processed_at": now.isoformat()},
                correlation_id=None,
            )
            processed += 1
        except Exception as e:
            new_attempts = attempts + 1
            if new_attempts >= MAX_RETRIES:
                new_status = "dead"
                next_retry_at = None
            else:
                new_status = "retrying"
                delay = RETRY_DELAYS_SECONDS[min(new_attempts, len(RETRY_DELAYS_SECONDS) - 1)]
                next_retry_at = (now + timedelta(seconds=delay)).isoformat()

            try:
                await svc.update(
                    table="webhook_dlq",
                    tenant_id=tenant_id,
                    actor_user_id=None,
                    record_id=uuid.UUID(str(item["id"])),
                    expected_version=item.get("version", 1),
                    patch={
                        "status": new_status,
                        "attempts": new_attempts,
                        "last_error": str(e),
                        "next_retry_at": next_retry_at,
                    },
                    correlation_id=None,
                )
            except Exception as update_err:
                logger.error("Failed to update DLQ item %s: %s", item["id"], update_err)

    return processed
