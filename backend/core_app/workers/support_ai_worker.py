from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from core_app.ai.service import AiService
from core_app.support.chat_service import ESCALATION_TRIGGERS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the FusionEMS Quantum support AI. Help EMS billing coordinators with questions "
    "about claims, documents, fax uploads, and platform features. Provide exact UI navigation "
    "paths when relevant. If you cannot help or detect urgency, offer to escalate to the founder. "
    "Always be professional and concise."
)


def lambda_handler(event: dict[str, Any], context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            task_type = body.get("task_type", "ai_reply")
            if task_type == "ai_reply":
                process_ai_reply(body)
            elif task_type == "ai_summarize":
                process_ai_summarize(body)
            else:
                logger.warning("support_ai_worker unknown task_type=%s", task_type)
        except Exception as exc:
            logger.exception(
                "support_ai_worker_record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            raise


def process_ai_reply(message: dict[str, Any]) -> None:
    thread_id: str = message.get("thread_id", "")
    tenant_id: str = message.get("tenant_id", "")
    trigger_message: str = message.get("trigger_message", "")

    correlation_id = message.get("correlation_id") or str(uuid.uuid4())
    logger.info("support_ai_reply_start thread_id=%s correlation_id=%s", thread_id, correlation_id)

    # Idempotency: check if AI already replied to this message
    last_msg_id = message.get("trigger_message_id", "")
    if last_msg_id:
        database_url_idem = os.environ.get("DATABASE_URL", "")
        if database_url_idem:
            try:
                import psycopg as _psycopg_idem

                with (
                    _psycopg_idem.connect(database_url_idem) as _conn_idem,
                    _conn_idem.cursor() as _cur_idem,
                ):
                    _cur_idem.execute(
                        "SELECT id FROM support_messages WHERE data->>'in_reply_to_message_id' = %s AND data->>'sender_role' = 'ai' LIMIT 1",
                        (last_msg_id,),
                    )
                    _existing_idem = _cur_idem.fetchone()
                if _existing_idem:
                    logger.info(
                        "support_ai_reply_skip_already_replied thread_id=%s correlation_id=%s",
                        thread_id,
                        correlation_id,
                    )
                    return {"skipped": True, "reason": "already_replied"}
            except Exception as _idem_exc:
                logger.warning(
                    "support_ai_reply_idempotency_check_failed thread_id=%s error=%s correlation_id=%s",
                    thread_id,
                    _idem_exc,
                    correlation_id,
                )

    if not thread_id or not tenant_id:
        logger.warning(
            "support_ai_reply_missing_fields thread_id=%s tenant_id=%s correlation_id=%s",
            thread_id,
            tenant_id,
            correlation_id,
        )
        return

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error(
            "support_ai_reply_no_db thread_id=%s correlation_id=%s", thread_id, correlation_id
        )
        return

    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, data FROM support_messages "
                    "WHERE data->>'thread_id' = %s AND deleted_at IS NULL "
                    "ORDER BY created_at ASC LIMIT 5",
                    (thread_id,),
                )
                rows = cur.fetchall()

            context_lines = []
            for row in rows:
                d = row[1] if isinstance(row[1], dict) else json.loads(row[1])
                role = d.get("sender_role", "user")
                context_lines.append(f"{role.upper()}: {d.get('content', '')}")
            context_block = "\n".join(context_lines)

            user_prompt = (
                f"Thread context (last messages):\n{context_block}\n\n"
                f"Current message: {trigger_message}"
            )

            try:
                ai = AiService()
                response_text, meta = ai.chat(system=SYSTEM_PROMPT, user=user_prompt)
            except Exception as exc:
                logger.error(
                    "support_ai_reply_ai_failed thread_id=%s error=%s correlation_id=%s",
                    thread_id,
                    exc,
                    correlation_id,
                )
                return

            low_confidence = (
                "i'm not sure" in response_text.lower() or "unclear" in response_text.lower()
            )
            turn_count = sum(
                1
                for row in rows
                if (row[1] if isinstance(row[1], dict) else json.loads(row[1])).get("sender_role")
                == "ai"
            )

            if low_confidence or turn_count >= 2:
                content_lower = trigger_message.lower()
                triggered_by = next(
                    (t for t in ESCALATION_TRIGGERS if t in content_lower), "ai_low_confidence"
                )
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE support_threads "
                        "SET data = data || %s::jsonb, updated_at = now() "
                        "WHERE id = %s",
                        (
                            json.dumps(
                                {
                                    "escalated": True,
                                    "status": "escalated",
                                    "escalation_reason": triggered_by,
                                }
                            ),
                            thread_id,
                        ),
                    )
                    cur.execute(
                        "INSERT INTO support_escalations (tenant_id, data) VALUES (%s, %s::jsonb)",
                        (
                            tenant_id,
                            json.dumps(
                                {
                                    "thread_id": thread_id,
                                    "tenant_id": tenant_id,
                                    "trigger": triggered_by,
                                    "escalated_at": datetime.now(UTC).isoformat(),
                                }
                            ),
                        ),
                    )

            ai_data = {
                "thread_id": thread_id,
                "sender_role": "ai",
                "sender_id": "ai",
                "content": response_text,
                "attachments": [],
                "sent_at": datetime.now(UTC).isoformat(),
                "read_by_founder": False,
                "ai_meta": meta,
            }
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO support_messages (tenant_id, data) VALUES (%s, %s::jsonb)",
                    (tenant_id, json.dumps(ai_data)),
                )
            conn.commit()

        logger.info(
            "support_ai_reply_done thread_id=%s low_confidence=%s correlation_id=%s",
            thread_id,
            low_confidence,
            correlation_id,
        )
    except Exception as exc:
        logger.error(
            "support_ai_reply_failed thread_id=%s error=%s correlation_id=%s",
            thread_id,
            exc,
            correlation_id,
        )


def process_ai_summarize(message: dict[str, Any]) -> None:
    thread_id: str = message.get("thread_id", "")
    tenant_id: str = message.get("tenant_id", "")

    correlation_id = message.get("correlation_id") or str(uuid.uuid4())
    logger.info(
        "support_ai_summarize_start thread_id=%s correlation_id=%s", thread_id, correlation_id
    )

    if not thread_id or not tenant_id:
        logger.warning(
            "support_ai_summarize_missing_fields thread_id=%s correlation_id=%s",
            thread_id,
            correlation_id,
        )
        return

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error(
            "support_ai_summarize_no_db thread_id=%s correlation_id=%s", thread_id, correlation_id
        )
        return

    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM support_messages "
                    "WHERE data->>'thread_id' = %s AND deleted_at IS NULL "
                    "ORDER BY created_at ASC",
                    (thread_id,),
                )
                rows = cur.fetchall()

            lines = []
            for row in rows:
                d = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                lines.append(f"{d.get('sender_role', 'user').upper()}: {d.get('content', '')}")
            transcript = "\n".join(lines)

            system = "You are a concise support thread analyst for the FusionEMS Quantum founder."
            user_prompt = (
                f"Summarize this support thread in 2-3 sentences for the founder. "
                f"Include: issue type, current status, any resolution or next action needed.\n\n"
                f"Thread:\n{transcript}"
            )

            try:
                ai = AiService()
                summary, _ = ai.chat(system=system, user=user_prompt)
            except Exception as exc:
                logger.error(
                    "support_ai_summarize_ai_failed thread_id=%s error=%s correlation_id=%s",
                    thread_id,
                    exc,
                    correlation_id,
                )
                return

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE support_threads "
                    "SET data = data || %s::jsonb, updated_at = now() "
                    "WHERE id = %s",
                    (json.dumps({"ai_summary": summary}), thread_id),
                )
            conn.commit()

        logger.info(
            "support_ai_summarize_done thread_id=%s correlation_id=%s", thread_id, correlation_id
        )
    except Exception as exc:
        logger.error(
            "support_ai_summarize_failed thread_id=%s error=%s correlation_id=%s",
            thread_id,
            exc,
            correlation_id,
        )
