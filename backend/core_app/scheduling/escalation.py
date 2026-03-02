from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

from core_app.repositories.domination_repository import DominationRepository


def run_coverage_escalations(
    *, db: Session, tenant_id: uuid.UUID, within_hours: int = 4
) -> dict[str, Any]:
    """
    Finds uncovered shift_instances within the next `within_hours` and creates paging events
    using escalation_policies.
    Deterministic: the same uncovered shift will not be paged twice within the same policy window
    because pages are de-duplicated by (shift_instance_id, policy_id).
    """
    shifts_repo = DominationRepository(db, table="shift_instances")
    assign_repo = DominationRepository(db, table="crew_assignments")
    rules_repo = DominationRepository(db, table="coverage_rulesets")
    pages_repo = DominationRepository(db, table="pages")

    now = dt.datetime.utcnow()
    horizon = now + dt.timedelta(hours=within_hours)

    shifts = shifts_repo.list(tenant_id=tenant_id, limit=5000)
    assignments = assign_repo.list(tenant_id=tenant_id, limit=10000)
    rulesets = rules_repo.list(tenant_id=tenant_id, limit=2000)
    pages = pages_repo.list(tenant_id=tenant_id, limit=5000)

    # Build assignment counts per shift_instance_id
    assigned_counts: dict[str, int] = {}
    for a in assignments:
        sid = a["data"].get("shift_instance_id")
        if sid:
            assigned_counts[sid] = assigned_counts.get(sid, 0) + 1

    # Choose first ruleset as active if multiple
    active_rules = rulesets[0]["data"] if rulesets else {}
    min_staff = int(active_rules.get("min_staff", 1))
    policy_id = active_rules.get("escalation_policy_id") or "default"

    existing_page_keys = {
        (p["data"].get("shift_instance_id"), p["data"].get("policy_id")) for p in pages
    }

    created: list[dict[str, Any]] = []
    for s in shifts:
        start = s["data"].get("start_at")
        if not start:
            continue
        try:
            start_dt = dt.datetime.fromisoformat(start.replace("Z", ""))
        except Exception:
            continue
        if not (now <= start_dt <= horizon):
            continue

        sid = str(s["id"])
        count = assigned_counts.get(sid, 0)
        if count >= min_staff:
            continue

        key = (sid, policy_id)
        if key in existing_page_keys:
            continue

        page = pages_repo.create(
            tenant_id=tenant_id,
            data={
                "reason": "coverage_unfilled",
                "shift_instance_id": sid,
                "policy_id": policy_id,
                "required": min_staff,
                "current": count,
                "status": "active",
                "created_at": now.isoformat(),
            },
        )
        created.append(page)

    return {"pages_created": len(created), "page_ids": [p["id"] for p in created]}
