from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

WEIGHTS = {
    "active_alerts": 40,
    "maintenance_state": 20,
    "mdt_online": 10,
    "obd_health": 20,
    "credential_compliance": 10,
}

MDT_OFFLINE_THRESHOLD_MINUTES = 15


class ReadinessEngine:
    def __init__(
        self, db: Session, publisher: EventPublisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID
    ) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id

    def compute_unit_readiness(self, unit_id: uuid.UUID) -> dict[str, Any]:
        uid = str(unit_id)
        now = datetime.now(UTC)

        alerts = self.svc.repo("fleet_alerts").list(tenant_id=self.tenant_id, limit=200)
        active_alerts = [
            a
            for a in alerts
            if (a.get("data") or {}).get("unit_id") == uid
            and not (a.get("data") or {}).get("acknowledged")
            and not (a.get("data") or {}).get("resolved")
        ]
        critical_alerts = [
            a for a in active_alerts if (a.get("data") or {}).get("severity") == "critical"
        ]
        alert_penalty = min(len(critical_alerts) * 25 + len(active_alerts) * 10, 100)
        alert_score = max(0, 100 - alert_penalty)

        maintenance_list = self.svc.repo("maintenance_work_orders").list(
            tenant_id=self.tenant_id, limit=100
        )
        unit_maintenance = [
            m for m in maintenance_list if (m.get("data") or {}).get("unit_id") == uid
        ]
        open_critical = [
            m
            for m in unit_maintenance
            if (m.get("data") or {}).get("status") not in ("completed", "cancelled")
            and (m.get("data") or {}).get("priority") in ("critical", "urgent")
        ]
        open_routine = [
            m
            for m in unit_maintenance
            if (m.get("data") or {}).get("status") not in ("completed", "cancelled")
            and (m.get("data") or {}).get("priority") not in ("critical", "urgent")
        ]
        maintenance_score = 100
        if open_critical:
            maintenance_score = 0
        elif open_routine:
            maintenance_score = max(0, 100 - len(open_routine) * 15)

        mdt_sessions = self.svc.repo("mdt_sessions").list(tenant_id=self.tenant_id, limit=100)
        unit_sessions = [s for s in mdt_sessions if (s.get("data") or {}).get("unit_id") == uid]
        mdt_online = False
        if unit_sessions:
            latest = sorted(unit_sessions, key=lambda x: x.get("updated_at", ""), reverse=True)[0]
            last_seen_str = latest.get("updated_at") or latest.get("created_at")
            if last_seen_str:
                try:
                    last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                    delta = (now - last_seen).total_seconds() / 60
                    mdt_online = delta < MDT_OFFLINE_THRESHOLD_MINUTES
                except Exception:
                    pass
        mdt_score = 100 if mdt_online else 0

        obd_readings = self.svc.repo("obd_readings").list(tenant_id=self.tenant_id, limit=50)
        unit_obd = [r for r in obd_readings if (r.get("data") or {}).get("unit_id") == uid]
        if unit_obd:
            latest_obd = sorted(unit_obd, key=lambda x: x.get("created_at", ""), reverse=True)[0]
            obd_data = (latest_obd.get("data") or {}).get("payload", {})
            fault_codes = obd_data.get("fault_codes", [])
            obd_score = max(0, 100 - len(fault_codes) * 20)
        else:
            obd_score = 50

        creds = self.svc.repo("credentials").list(tenant_id=self.tenant_id, limit=500)
        unit_crews = self.svc.repo("crew_assignments").list(tenant_id=self.tenant_id, limit=100)
        unit_crew_ids = [
            (ca.get("data") or {}).get("crew_member_id")
            for ca in unit_crews
            if (ca.get("data") or {}).get("unit_id") == uid
        ]
        if unit_crew_ids:
            expired_creds = [
                c
                for c in creds
                if (c.get("data") or {}).get("crew_member_id") in unit_crew_ids
                and (c.get("data") or {}).get("expires_at")
                and datetime.fromisoformat(
                    (c.get("data") or {}).get("expires_at", "2099-01-01").replace("Z", "+00:00")
                )
                < now
            ]
            credential_score = max(0, 100 - len(expired_creds) * 20)
        else:
            credential_score = 100

        weighted = (
            alert_score * WEIGHTS["active_alerts"] / 100
            + maintenance_score * WEIGHTS["maintenance_state"] / 100
            + mdt_score * WEIGHTS["mdt_online"] / 100
            + obd_score * WEIGHTS["obd_health"] / 100
            + credential_score * WEIGHTS["credential_compliance"] / 100
        )

        return {
            "unit_id": uid,
            "readiness_score": round(weighted),
            "components": {
                "alert_score": alert_score,
                "maintenance_score": maintenance_score,
                "mdt_score": mdt_score,
                "obd_score": obd_score,
                "credential_score": credential_score,
            },
            "active_alert_count": len(active_alerts),
            "critical_alert_count": len(critical_alerts),
            "open_maintenance_count": len(open_critical) + len(open_routine),
            "mdt_online": mdt_online,
            "computed_at": now.isoformat(),
        }

    async def persist_readiness(
        self, unit_id: uuid.UUID, correlation_id: str | None = None
    ) -> dict[str, Any]:
        result = self.compute_unit_readiness(unit_id)
        saved = await self.svc.create(
            table="readiness_scores",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data=result,
            correlation_id=correlation_id,
        )
        return {**result, "record_id": str(saved["id"])}

    def fleet_summary(self) -> dict[str, Any]:
        units = self.svc.repo("units").list(tenant_id=self.tenant_id, limit=200)
        scores = []
        for unit in units:
            uid = uuid.UUID(str(unit["id"]))
            try:
                score = self.compute_unit_readiness(uid)
                scores.append(score)
            except Exception:
                pass
        if not scores:
            return {
                "fleet_count": 0,
                "avg_readiness": 0,
                "units_ready": 0,
                "units_limited": 0,
                "units_no_go": 0,
                "scores": [],
            }
        avg = round(sum(s["readiness_score"] for s in scores) / len(scores))
        return {
            "fleet_count": len(scores),
            "avg_readiness": avg,
            "units_ready": sum(1 for s in scores if s["readiness_score"] >= 80),
            "units_limited": sum(1 for s in scores if 40 <= s["readiness_score"] < 80),
            "units_no_go": sum(1 for s in scores if s["readiness_score"] < 40),
            "scores": sorted(scores, key=lambda x: x["readiness_score"]),
        }
