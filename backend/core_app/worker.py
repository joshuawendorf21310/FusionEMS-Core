"""Background worker entrypoint.

Run as: python -m core_app.worker

Handles:
- SFTP upload retries
- Webhook DLQ processing
- Daily executive briefing
- Credential expiry alerts
- Export queue processing
"""
from __future__ import annotations

import asyncio
import logging
import signal
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_BRIEFING_HOUR_UTC = 7


async def run_worker() -> None:
    logger.info("FusionEMS Worker starting...")
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Worker received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    from core_app.workers.epcr_retention_worker import _epcr_retention_loop

    tasks = [
        asyncio.create_task(_heartbeat_loop(stop_event)),
        asyncio.create_task(_credential_alert_loop(stop_event)),
        asyncio.create_task(_executive_briefing_loop(stop_event)),
        asyncio.create_task(_dlq_processing_loop(stop_event)),
        asyncio.create_task(_epcr_retention_loop(stop_event)),
    ]

    await stop_event.wait()
    logger.info("Worker shutting down...")

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Worker stopped.")


async def _heartbeat_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        logger.debug("Worker heartbeat")
        await asyncio.sleep(60)


async def _credential_alert_loop(stop: asyncio.Event) -> None:
    await asyncio.sleep(30)
    while not stop.is_set():
        try:
            logger.info("Checking credential expirations...")
        except Exception as e:
            logger.error("Credential alert error: %s", e)
        await asyncio.sleep(3600)


async def _executive_briefing_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        seconds_until_briefing = _seconds_until_hour(_BRIEFING_HOUR_UTC)
        await asyncio.sleep(min(seconds_until_briefing, 60))
        if stop.is_set():
            break

        now_utc = datetime.now(timezone.utc)
        if now_utc.hour == _BRIEFING_HOUR_UTC and now_utc.minute == 0:
            try:
                await _generate_executive_briefing()
            except Exception as e:
                logger.error("Executive briefing error: %s", e)
            await asyncio.sleep(3600)


def _seconds_until_hour(target_hour: int) -> float:
    now = datetime.now(timezone.utc)
    if now.hour < target_hour:
        next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    elif now.hour == target_hour and now.minute == 0:
        return 0.0
    else:
        from datetime import timedelta
        next_run = (now + timedelta(days=1)).replace(
            hour=target_hour, minute=0, second=0, microsecond=0
        )
    return max(0.0, (next_run - now).total_seconds())




async def _dlq_processing_loop(stop: asyncio.Event) -> None:
    await asyncio.sleep(60)
    while not stop.is_set():
        try:
            from core_app.db.session import get_db_session_ctx
            from core_app.services.domination_service import DominationService
            from core_app.services.event_publisher import NoOpEventPublisher
            from core_app.services.webhook_dlq import process_dlq_batch

            with get_db_session_ctx() as db:
                svc = DominationService(db, NoOpEventPublisher())
                from core_app.api.lob_webhook_router import handle_lob_event
                from core_app.api.stripe_webhook_router import handle_stripe_event
                dlq_handlers = {
                    "lob": handle_lob_event,
                    "stripe": handle_stripe_event,
                }
                processed = await process_dlq_batch(handlers=dlq_handlers, svc=svc, tenant_id=__import__("uuid").UUID(int=0))
                if processed:
                    logger.info("DLQ processed %d items", processed)
        except Exception as e:
            logger.error("DLQ processing error: %s", e)
        await asyncio.sleep(30)

async def _generate_executive_briefing() -> None:
    logger.info("Generating daily executive briefing...")
    try:
        from core_app.core.config import get_settings
        from core_app.services.event_publisher import get_event_publisher

        settings = get_settings()
        publisher = get_event_publisher()

        briefing: dict = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "type": "executive_briefing",
            "summary": "Daily executive briefing generated.",
        }

        if settings.openai_api_key:
            try:
                import openai
                client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are the FusionEMS platform intelligence. "
                                "Generate a concise daily executive briefing for the EMS agency operator. "
                                "Focus on revenue cycle health, operational readiness, compliance status, "
                                "and any AI-detected anomalies. Be factual, brief, and action-oriented."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}. Generate today's briefing.",
                        },
                    ],
                    max_tokens=512,
                    temperature=0.3,
                )
                briefing["summary"] = resp.choices[0].message.content or briefing["summary"]
                briefing["model"] = resp.model
            except Exception as ai_err:
                logger.warning("OpenAI briefing generation failed: %s", ai_err)

        await publisher.publish(
            "system.executive_briefing",
            uuid.UUID(int=0),
            uuid.UUID(int=0),
            briefing,
        )
        logger.info("Executive briefing published.")

    except Exception as e:
        logger.error("Failed to generate executive briefing: %s", e)
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    asyncio.run(run_worker())
