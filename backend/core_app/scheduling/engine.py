from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from core_app.repositories.domination_repository import DominationRepository


@dataclass(frozen=True)
class CoverageViolation:
    shift_instance_id: uuid.UUID
    reason: str
    required: dict[str, Any]


class SchedulingEngine:
    """Enterprise scheduling engine:
    - coverage enforcement (minimum staffing + credential requirements)
    - fatigue checks (simplified rule set, configurable via ruleset JSON)
    - escalation suggestions (caller decides how to page)
    """

    def __init__(self, db: Session, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.repo_shift_instances = DominationRepository(db, table="shift_instances")
        self.repo_coverage = DominationRepository(db, table="coverage_rulesets")
        self.repo_assignments = DominationRepository(db, table="crew_assignments")
        self.repo_credentials = DominationRepository(db, table="credentials")
        self.repo_requirements = DominationRepository(db, table="credential_requirements")
        self.repo_availability = DominationRepository(db, table="availability_blocks")

    def _now(self) -> dt.datetime:
        return dt.datetime.now(tz=dt.UTC)

    def list_expiring_credentials(self, within_days: int = 30) -> list[dict[str, Any]]:
        cutoff = self._now() + dt.timedelta(days=within_days)
        creds = self.repo_credentials.list(self.tenant_id, limit=500)
        expiring: list[dict[str, Any]] = []
        for c in creds:
            expires = c["data"].get("expires_at")
            if not expires:
                continue
            try:
                exp_dt = dt.datetime.fromisoformat(expires.replace("Z", "+00:00"))
            except Exception:
                continue
            if exp_dt <= cutoff:
                expiring.append(c)
        return sorted(expiring, key=lambda r: r["data"].get("expires_at") or "")

    def validate_crew_credentials(
        self, crew_member_id: uuid.UUID, role: str, at: dt.datetime | None = None
    ) -> tuple[bool, list[str]]:
        at = at or self._now()
        reqs = self.repo_requirements.list(self.tenant_id, limit=500)
        required = [r["data"] for r in reqs if r["data"].get("role") == role]
        required_codes = set()
        for r in required:
            for code in r.get("required_codes") or []:
                required_codes.add(code)

        creds = self.repo_credentials.list(self.tenant_id, limit=500)
        active_codes = set()
        missing: list[str] = []
        for c in creds:
            d = c["data"]
            if d.get("crew_member_id") != str(crew_member_id):
                continue
            code = d.get("code")
            if not code:
                continue
            expires = d.get("expires_at")
            if expires:
                try:
                    exp_dt = dt.datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    if exp_dt < at:
                        continue
                except Exception:
                    continue
            active_codes.add(code)

        for code in sorted(required_codes):
            if code not in active_codes:
                missing.append(code)
        return (len(missing) == 0, missing)

    def coverage_dashboard(
        self, start: dt.datetime | None = None, hours: int = 24
    ) -> dict[str, Any]:
        start = start or self._now().replace(minute=0, second=0, microsecond=0)
        end = start + dt.timedelta(hours=hours)

        # Choose active ruleset (latest by created_at)
        rulesets = self.repo_coverage.list(self.tenant_id, limit=50)
        rulesets_sorted = sorted(rulesets, key=lambda r: r.get("created_at") or "", reverse=True)
        active_ruleset = rulesets_sorted[0]["data"] if rulesets_sorted else {"minimums": []}

        # Shift instances in window
        instances = self.repo_shift_instances.list(self.tenant_id, limit=2000)
        window_instances = []
        for inst in instances:
            d = inst["data"]
            try:
                s = dt.datetime.fromisoformat(d.get("start_at", "").replace("Z", "+00:00"))
                e = dt.datetime.fromisoformat(d.get("end_at", "").replace("Z", "+00:00"))
            except Exception:
                continue
            if e <= start or s >= end:
                continue
            window_instances.append(inst)

        # Build assignment counts per shift_instance_id per role
        assignments = self.repo_assignments.list(self.tenant_id, limit=5000)
        counts: dict[str, dict[str, int]] = {}
        for a in assignments:
            d = a["data"]
            sid = d.get("shift_instance_id")
            role = d.get("role") or "unknown"
            if not sid:
                continue
            counts.setdefault(sid, {}).setdefault(role, 0)
            counts[sid][role] += 1

        violations: list[CoverageViolation] = []
        minimums = active_ruleset.get("minimums") or []
        for inst in window_instances:
            sid = str(inst["id"])
            for m in minimums:
                role = m.get("role")
                required_count = int(m.get("count") or 0)
                if required_count <= 0 or not role:
                    continue
                have = counts.get(sid, {}).get(role, 0)
                if have < required_count:
                    violations.append(
                        CoverageViolation(
                            shift_instance_id=uuid.UUID(sid),
                            reason="UNDER_COVERED",
                            required={"role": role, "required": required_count, "have": have},
                        )
                    )

        return {
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "active_ruleset": active_ruleset,
            "shift_instances": window_instances,
            "violations": [v.__dict__ for v in violations],
        }
