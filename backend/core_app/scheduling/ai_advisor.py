from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core_app.ai.service import AiService
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

SYSTEM_PROMPT = """You are an expert EMS scheduling advisor for QuantumEMS.
You analyze historical call volume, crew fatigue data, overtime projections, unit readiness scores, and credential gaps.
You produce structured scheduling suggestions and risk windows for human review.
Rules:
- Never invent facts. Only reference data provided.
- All suggestions require human approval before any schedule change.
- Flag fatigue risk if any crew member has worked >12 hours in last 24h or >48h in last 7 days.
- Flag overtime risk if projected hours exceed 40/week.
- Flag credential gaps if required credentials are missing or expiring within 14 days.
- Output valid JSON only.
"""

DRAFT_SCHEMA = {
    "summary": "string — 1-2 sentences",
    "risk_windows": [{"start": "ISO datetime", "end": "ISO datetime", "reason": "string", "severity": "low|medium|high"}],
    "coverage_gaps": [{"shift_instance_id": "uuid", "gap_reason": "string"}],
    "suggestions": [{"action": "string", "detail": "string", "priority": "low|medium|high"}],
    "overtime_risk_crew": ["crew_member_id strings"],
    "fatigue_risk_crew": ["crew_member_id strings"],
    "confidence": "float 0-1",
}


class AISchedulingAdvisor:
    def __init__(self, db: Session, publisher: EventPublisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id
        self.ai = AiService()

    def _build_context(self, horizon_hours: int = 48) -> dict[str, Any]:
        shifts = self.svc.repo("shift_instances").list(tenant_id=self.tenant_id, limit=200)
        assignments = self.svc.repo("crew_assignments").list(tenant_id=self.tenant_id, limit=500)
        creds = self.svc.repo("credentials").list(tenant_id=self.tenant_id, limit=500)
        readiness = self.svc.repo("readiness_scores").list(tenant_id=self.tenant_id, limit=100)
        now = datetime.now(UTC).isoformat()

        assigned_ids = {(a.get("data") or {}).get("shift_instance_id") for a in assignments}
        upcoming_uncovered = [
            s for s in shifts
            if str(s["id"]) not in assigned_ids
        ][:20]

        expiring_soon = [
            c for c in creds
            if (c.get("data") or {}).get("expires_at", "2099-01-01") < "2026-03-13"
        ][:10]

        latest_readiness = {}
        for r in readiness:
            uid = (r.get("data") or {}).get("unit_id")
            if uid and uid not in latest_readiness:
                latest_readiness[uid] = (r.get("data") or {}).get("readiness_score", 0)

        return {
            "now": now,
            "horizon_hours": horizon_hours,
            "upcoming_uncovered_shifts": [
                {"id": str(s["id"]), "data": s.get("data")} for s in upcoming_uncovered
            ],
            "expiring_credentials": [
                {"id": str(c["id"]), "data": c.get("data")} for c in expiring_soon
            ],
            "unit_readiness_summary": latest_readiness,
            "total_assignments": len(assignments),
            "total_shifts": len(shifts),
        }

    async def generate_draft(
        self, horizon_hours: int = 48, correlation_id: str | None = None
    ) -> dict[str, Any]:
        context = self._build_context(horizon_hours)
        user_msg = (
            f"Analyze this scheduling context and return a JSON object matching this schema:\n"
            f"{json.dumps(DRAFT_SCHEMA, indent=2)}\n\n"
            f"Context:\n{json.dumps(context, indent=2, default=str)}"
        )
        try:
            raw, usage = self.ai.chat(system=SYSTEM_PROMPT, user=user_msg, max_tokens=2048)
            try:
                draft = json.loads(raw)
            except json.JSONDecodeError:
                import re
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                draft = json.loads(m.group(0)) if m else {"summary": raw, "suggestions": [], "confidence": 0.3}
        except Exception as exc:
            draft = {
                "summary": f"AI advisor unavailable: {exc}",
                "risk_windows": [],
                "coverage_gaps": [],
                "suggestions": [],
                "overtime_risk_crew": [],
                "fatigue_risk_crew": [],
                "confidence": 0.0,
            }
            usage = {}

        record = await self.svc.create(
            table="ai_scheduling_drafts",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "draft": draft,
                "context_snapshot": context,
                "horizon_hours": horizon_hours,
                "ai_usage": usage,
                "status": "pending_review",
                "reviewed_by": None,
                "approved": None,
                "generated_at": datetime.now(UTC).isoformat(),
            },
            correlation_id=correlation_id,
        )
        return {"draft_id": str(record["id"]), "draft": draft, "status": "pending_review"}

    async def approve_draft(
        self, draft_id: uuid.UUID, correlation_id: str | None = None
    ) -> dict[str, Any]:
        record = self.svc.repo("ai_scheduling_drafts").get(tenant_id=self.tenant_id, record_id=draft_id)
        if not record:
            raise ValueError("draft_not_found")
        data = dict(record.get("data") or {})
        data["status"] = "approved"
        data["approved"] = True
        data["reviewed_by"] = str(self.actor_user_id)
        data["reviewed_at"] = datetime.now(UTC).isoformat()
        updated = await self.svc.update(
            table="ai_scheduling_drafts",
            tenant_id=self.tenant_id,
            record_id=draft_id,
            actor_user_id=self.actor_user_id,
            patch=data,
            expected_version=record.get("version", 1),
            correlation_id=correlation_id,
        )
        return updated

    def what_if_simulate(self, scenario: dict[str, Any]) -> dict[str, Any]:
        shifts = self.svc.repo("shift_instances").list(tenant_id=self.tenant_id, limit=500)
        assignments = self.svc.repo("crew_assignments").list(tenant_id=self.tenant_id, limit=1000)

        added_assignments = scenario.get("add_assignments", [])
        removed_assignment_ids = set(str(r) for r in scenario.get("remove_assignments", []))
        simulated_assignments = [
            a for a in assignments if str(a["id"]) not in removed_assignment_ids
        ] + added_assignments

        assigned_counts: dict[str, int] = {}
        for a in simulated_assignments:
            sid = (a.get("data") or {}).get("shift_instance_id") or a.get("shift_instance_id")
            if sid:
                assigned_counts[str(sid)] = assigned_counts.get(str(sid), 0) + 1

        uncovered = [s for s in shifts if assigned_counts.get(str(s["id"]), 0) == 0]
        coverage_pct = round((1 - len(uncovered) / max(len(shifts), 1)) * 100)

        crew_hours: dict[str, float] = {}
        for a in simulated_assignments:
            d = a.get("data") or a
            crew_id = str(d.get("crew_member_id") or d.get("user_id") or "")
            hours = float(d.get("hours", 12))
            crew_hours[crew_id] = crew_hours.get(crew_id, 0) + hours

        overtime_risk = [k for k, v in crew_hours.items() if v > 40]
        fatigue_risk = [k for k, v in crew_hours.items() if v > 48]

        return {
            "scenario": scenario,
            "coverage_pct": coverage_pct,
            "uncovered_shift_count": len(uncovered),
            "total_shift_count": len(shifts),
            "overtime_risk_count": len(overtime_risk),
            "fatigue_risk_count": len(fatigue_risk),
            "simulated_at": datetime.now(UTC).isoformat(),
        }
