from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any

from core_app.services.domination_service import DominationService
from core_app.ai.service import AiService

ESCALATION_TRIGGERS = [
    "urgent", "lawsuit", "legal action", "hipaa violation", "breach",
    "complaint", "attorney", "sue", "fraud", "human", "speak to someone",
    "escalate", "call me", "not working", "legal notice",
]

ESCALATION_DOLLAR_THRESHOLD = 10000


class ChatService:
    def __init__(self, db, publisher, tenant_id: str, user_id: str) -> None:
        self.svc = DominationService(db, publisher)
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def create_thread(self, thread_type: str, title: str, claim_id: str = None) -> dict:
        import asyncio
        from sqlalchemy import text
        import json

        data = {
            "thread_type": thread_type,
            "title": title,
            "claim_id": claim_id,
            "status": "open",
            "created_by": self.user_id,
            "ai_active": True,
            "escalated": False,
            "unread_founder": True,
        }
        row = self.db.execute(
            text(
                "INSERT INTO support_threads (tenant_id, data) "
                "VALUES (:tenant_id, CAST(:data AS jsonb)) "
                "RETURNING id, tenant_id, data, version, created_at, updated_at"
            ),
            {"tenant_id": self.tenant_id, "data": json.dumps(data, separators=(",", ":"))},
        ).mappings().one()
        self.db.commit()
        rec = dict(row)

        self.svc.publisher.publish_sync(
            event_name="chat.thread_created",
            tenant_id=uuid.UUID(self.tenant_id),
            entity_id=rec["id"],
            entity_type="support_threads",
            payload={"thread_id": str(rec["id"]), "thread_type": thread_type, "title": title},
        )
        return rec

    def send_message(
        self,
        thread_id: str,
        content: str,
        attachments: list = None,
        sender_role: str = "agency",
    ) -> dict:
        from sqlalchemy import text
        import json

        data = {
            "thread_id": thread_id,
            "sender_role": sender_role,
            "sender_id": self.user_id,
            "content": content,
            "attachments": attachments or [],
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "read_by_founder": False,
        }
        row = self.db.execute(
            text(
                "INSERT INTO support_messages (tenant_id, data) "
                "VALUES (:tenant_id, CAST(:data AS jsonb)) "
                "RETURNING id, tenant_id, data, version, created_at, updated_at"
            ),
            {"tenant_id": self.tenant_id, "data": json.dumps(data, separators=(",", ":"))},
        ).mappings().one()
        self.db.commit()
        rec = dict(row)

        self.svc.publisher.publish_sync(
            event_name="chat.message_received",
            tenant_id=uuid.UUID(self.tenant_id),
            entity_id=rec["id"],
            entity_type="support_messages",
            payload={"thread_id": thread_id, "sender_role": sender_role},
        )

        self._check_escalation(thread_id, content)

        thread = self._get_thread(thread_id)
        if thread and thread.get("data", {}).get("ai_active") and sender_role != "ai":
            self._queue_ai_reply(thread_id, content)

        return rec

    def _get_thread(self, thread_id: str) -> dict | None:
        from sqlalchemy import text
        row = self.db.execute(
            text(
                "SELECT id, tenant_id, data, version, created_at, updated_at "
                "FROM support_threads "
                "WHERE id = :id AND deleted_at IS NULL"
            ),
            {"id": thread_id},
        ).mappings().first()
        return dict(row) if row else None

    def _check_escalation(self, thread_id: str, content: str) -> bool:
        from sqlalchemy import text
        import json

        content_lower = content.lower()
        triggered_by = None
        for trigger in ESCALATION_TRIGGERS:
            if trigger in content_lower:
                triggered_by = trigger
                break

        if not triggered_by:
            return False

        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            text(
                "UPDATE support_threads "
                "SET data = data || CAST(:patch AS jsonb), updated_at = now() "
                "WHERE id = :id"
            ),
            {
                "id": thread_id,
                "patch": json.dumps(
                    {"escalated": True, "status": "escalated", "escalation_reason": triggered_by},
                    separators=(",", ":"),
                ),
            },
        )

        esc_data = {
            "thread_id": thread_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "trigger": triggered_by,
            "trigger_content": content[:500],
            "escalated_at": now,
        }
        self.db.execute(
            text(
                "INSERT INTO support_escalations (tenant_id, data) "
                "VALUES (:tenant_id, CAST(:data AS jsonb))"
            ),
            {
                "tenant_id": self.tenant_id,
                "data": json.dumps(esc_data, separators=(",", ":")),
            },
        )
        self.db.commit()

        self.svc.publisher.publish_sync(
            event_name="chat.escalated",
            tenant_id=uuid.UUID(self.tenant_id),
            entity_id=uuid.UUID(thread_id),
            entity_type="support_threads",
            payload={"thread_id": thread_id, "trigger": triggered_by},
        )
        return True

    def _queue_ai_reply(self, thread_id: str, user_message: str) -> None:
        from sqlalchemy import text
        import json

        messages = self.get_thread_messages(thread_id, limit=5)
        context_lines = []
        for m in messages:
            d = m.get("data", {})
            role = d.get("sender_role", "user")
            context_lines.append(f"{role.upper()}: {d.get('content', '')}")
        context_block = "\n".join(context_lines)

        system = (
            "You are the FusionEMS Quantum support AI. Help EMS billing coordinators with questions "
            "about claims, documents, fax uploads, and platform features. Provide exact UI navigation "
            "paths when relevant. If you cannot help or detect urgency, offer to escalate to the founder. "
            "Always be professional and concise."
        )
        user_prompt = (
            f"Thread context (last messages):\n{context_block}\n\n"
            f"Current message: {user_message}"
        )

        try:
            ai = AiService()
            response_text, meta = ai.chat(system=system, user=user_prompt)
        except Exception:
            return

        low_confidence = "i'm not sure" in response_text.lower() or "unclear" in response_text.lower()

        turn_count = sum(
            1 for m in messages if m.get("data", {}).get("sender_role") == "ai"
        )
        if low_confidence or turn_count >= 2:
            self._check_escalation(thread_id, "escalate")

        ai_data = {
            "thread_id": thread_id,
            "sender_role": "ai",
            "sender_id": "ai",
            "content": response_text,
            "attachments": [],
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "read_by_founder": False,
            "ai_meta": meta,
        }
        self.db.execute(
            text(
                "INSERT INTO support_messages (tenant_id, data) "
                "VALUES (:tenant_id, CAST(:data AS jsonb))"
            ),
            {
                "tenant_id": self.tenant_id,
                "data": json.dumps(ai_data, separators=(",", ":")),
            },
        )
        self.db.commit()

    def get_thread_messages(self, thread_id: str, limit: int = 50) -> list[dict]:
        from sqlalchemy import text
        rows = self.db.execute(
            text(
                "SELECT id, tenant_id, data, version, created_at, updated_at "
                "FROM support_messages "
                "WHERE data->>'thread_id' = :thread_id AND deleted_at IS NULL "
                "ORDER BY created_at ASC "
                "LIMIT :limit"
            ),
            {"thread_id": thread_id, "limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]

    def mark_thread_read_by_founder(self, thread_id: str) -> None:
        from sqlalchemy import text
        import json

        self.db.execute(
            text(
                "UPDATE support_threads "
                "SET data = data || CAST(:patch AS jsonb), updated_at = now() "
                "WHERE id = :id"
            ),
            {"id": thread_id, "patch": json.dumps({"unread_founder": False}, separators=(",", ":"))},
        )
        self.db.execute(
            text(
                "UPDATE support_messages "
                "SET data = data || CAST(:patch AS jsonb), updated_at = now() "
                "WHERE data->>'thread_id' = :thread_id"
            ),
            {
                "thread_id": thread_id,
                "patch": json.dumps({"read_by_founder": True}, separators=(",", ":")),
            },
        )
        self.db.commit()

    def generate_thread_summary(self, thread_id: str) -> str:
        messages = self.get_thread_messages(thread_id, limit=200)
        lines = []
        for m in messages:
            d = m.get("data", {})
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
            summary = f"Summary unavailable: {exc}"
        return summary
