from __future__ import annotations

import uuid
from datetime import UTC, datetime

from core_app.ai.service import AiService
from core_app.services.domination_service import DominationService

ESCALATION_TRIGGERS = [
    "urgent",
    "lawsuit",
    "legal action",
    "hipaa violation",
    "breach",
    "complaint",
    "attorney",
    "sue",
    "fraud",
    "human",
    "speak to someone",
    "escalate",
    "call me",
    "not working",
    "legal notice",
]

ESCALATION_DOLLAR_THRESHOLD = 10000


class ChatService:
    def __init__(self, db, publisher, tenant_id: str, user_id: str) -> None:
        self.svc = DominationService(db, publisher)
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def create_thread(self, thread_type: str, title: str, claim_id: str = None) -> dict:
        record = await self.svc.create(
            table="support_threads",
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            data={
                "thread_type": thread_type,
                "title": title,
                "status": "open",
                "claim_id": str(claim_id) if claim_id else None,
                "unread_founder": True,
                "escalated": False,
                "message_count": 0,
                "last_message_at": datetime.now(UTC).isoformat(),
            },
            correlation_id=None,
        )
        return record

    async def send_message(
        self,
        thread_id: str,
        content: str,
        attachments: list = None,
        sender_role: str = "agency",
    ) -> dict:

        msg = await self.svc.create(
            table="support_messages",
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            data={
                "thread_id": str(thread_id),
                "content": content,
                "sender_role": sender_role,
                "attachments": attachments or [],
                "is_read": False,
                "in_reply_to_message_id": None,
            },
            correlation_id=None,
        )

        thread = self.svc.repo("support_threads").get(tenant_id=self.tenant_id, record_id=thread_id)
        if thread:
            current_data = thread.get("data") or {}
            current_data["last_message_at"] = datetime.now(UTC).isoformat()
            current_data["message_count"] = current_data.get("message_count", 0) + 1
            if sender_role == "agency":
                current_data["unread_founder"] = True
            await self.svc.update(
                table="support_threads",
                tenant_id=self.tenant_id,
                record_id=thread_id,
                actor_user_id=self.user_id,
                expected_version=thread.get("version", 1),
                patch=current_data,
                correlation_id=None,
            )

        self.svc.publisher.publish_sync(
            event_name="chat.message_received",
            tenant_id=uuid.UUID(self.tenant_id),
            entity_id=msg["id"],
            entity_type="support_messages",
            payload={"thread_id": thread_id, "sender_role": sender_role},
        )

        await self._check_escalation(thread_id, content)

        thread = self._get_thread(thread_id)
        if thread and thread.get("data", {}).get("ai_active") and sender_role != "ai":
            self._queue_ai_reply(thread_id, content)

        return msg

    def _get_thread(self, thread_id: str) -> dict | None:
        from sqlalchemy import text

        row = (
            self.db.execute(
                text(
                    "SELECT id, tenant_id, data, version, created_at, updated_at "
                    "FROM support_threads "
                    "WHERE id = :id AND deleted_at IS NULL"
                ),
                {"id": thread_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    async def _check_escalation(self, thread_id: str, content: str) -> bool:
        content_lower = content.lower()
        triggered_by = None
        for trigger in ESCALATION_TRIGGERS:
            if trigger in content_lower:
                triggered_by = trigger
                break

        if not triggered_by:
            return False

        await self.svc.create(
            table="support_escalations",
            tenant_id=self.tenant_id,
            actor_user_id=self.user_id,
            data={
                "thread_id": str(thread_id),
                "trigger_phrase": triggered_by,
                "escalated_at": datetime.now(UTC).isoformat(),
                "resolved": False,
            },
            correlation_id=None,
        )

        thread = self.svc.repo("support_threads").get(tenant_id=self.tenant_id, record_id=thread_id)
        if thread:
            current_data = thread.get("data") or {}
            current_data["escalated"] = True
            current_data["status"] = "escalated"
            await self.svc.update(
                table="support_threads",
                tenant_id=self.tenant_id,
                record_id=thread_id,
                actor_user_id=self.user_id,
                expected_version=thread.get("version", 1),
                patch=current_data,
                correlation_id=None,
            )

        self.svc.publisher.publish_sync(
            event_name="chat.escalated",
            tenant_id=uuid.UUID(self.tenant_id),
            entity_id=uuid.UUID(thread_id),
            entity_type="support_threads",
            payload={"thread_id": thread_id, "trigger": triggered_by},
        )
        return True

    def _queue_ai_reply(self, thread_id: str, user_message: str) -> None:
        import json

        from sqlalchemy import text

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
            f"Thread context (last messages):\n{context_block}\n\nCurrent message: {user_message}"
        )

        try:
            ai = AiService()
            response_text, meta = ai.chat(system=system, user=user_prompt)
        except Exception:
            return

        low_confidence = (
            "i'm not sure" in response_text.lower() or "unclear" in response_text.lower()
        )

        turn_count = sum(1 for m in messages if m.get("data", {}).get("sender_role") == "ai")
        if low_confidence or turn_count >= 2:
            import asyncio

            asyncio.create_task(self._check_escalation(thread_id, "escalate"))

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

        rows = (
            self.db.execute(
                text(
                    "SELECT id, tenant_id, data, version, created_at, updated_at "
                    "FROM support_messages "
                    "WHERE data->>'thread_id' = :thread_id AND deleted_at IS NULL "
                    "ORDER BY created_at ASC "
                    "LIMIT :limit"
                ),
                {"thread_id": thread_id, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    async def mark_thread_read_by_founder(self, thread_id: str) -> None:
        import json

        from sqlalchemy import text

        thread = self.svc.repo("support_threads").get(tenant_id=self.tenant_id, record_id=thread_id)
        if thread:
            current_data = thread.get("data") or {}
            current_data["unread_founder"] = False
            await self.svc.update(
                table="support_threads",
                tenant_id=self.tenant_id,
                record_id=thread_id,
                actor_user_id=self.user_id,
                expected_version=thread.get("version", 1),
                patch=current_data,
                correlation_id=None,
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
