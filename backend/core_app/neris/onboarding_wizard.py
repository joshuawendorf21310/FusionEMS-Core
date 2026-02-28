from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

ONBOARDING_STEPS = [
    {"id": "department_identity", "label": "Department Identity", "required": True},
    {"id": "reporting_mode", "label": "Reporting Mode", "required": True},
    {"id": "stations", "label": "Fire Stations", "required": True},
    {"id": "apparatus", "label": "Apparatus & Units", "required": True},
    {"id": "personnel", "label": "Personnel (Optional)", "required": False},
    {"id": "pack_assignment", "label": "NERIS Pack Assignment", "required": True},
    {"id": "sample_incident", "label": "Create & Validate Sample Incident", "required": True},
    {"id": "golive_checklist", "label": "Go-Live Checklist", "required": True},
]

WI_DSPS_GOLIVE_CHECKLIST = [
    "Confirm department identifiers match DSPS records",
    "Verify primary contact information is current",
    "Ensure all apparatus have valid NERIS unit type codes",
    "Complete at least one sample incident with zero validation errors",
    "Review and save Go-Live checklist for department records",
    "Contact your NERIS vendor coordinator when ready to begin production reporting",
    "Schedule department training on RMS incident entry workflow",
    "Confirm reporting start date with Wisconsin DSPS (if applicable)",
]


class NERISOnboardingWizard:
    def __init__(self, db: Session, publisher: EventPublisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id

    async def start_onboarding(
        self,
        department_name: str,
        state: str = "WI",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        # Check for existing onboarding
        existing = self.svc.repo("neris_onboarding").list(tenant_id=self.tenant_id, limit=5)
        for o in existing:
            if not (o.get("data") or {}).get("completed_at"):
                return {"onboarding": o, "department": self._get_department((o.get("data") or {}).get("department_id")), "steps": ONBOARDING_STEPS}

        # Create department entity
        dept = await self.svc.create(
            table="fire_departments",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "name": department_name,
                "state": state.upper(),
                "status": "onboarding",
                "neris_pack_id": None,
                "primary_contact_name": "",
                "primary_contact_email": "",
                "primary_contact_phone": "",
            },
            correlation_id=correlation_id,
        )

        step_status = {step["id"]: "pending" for step in ONBOARDING_STEPS}

        onboarding = await self.svc.create(
            table="neris_onboarding",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "department_id": str(dept["id"]),
                "step_status_json": step_status,
                "completed_at": None,
                "state": state.upper(),
                "wi_dsps_checklist": {item: False for item in WI_DSPS_GOLIVE_CHECKLIST},
            },
            correlation_id=correlation_id,
        )
        return {"onboarding": onboarding, "department": dept, "steps": ONBOARDING_STEPS}

    def get_status(self) -> dict[str, Any] | None:
        records = self.svc.repo("neris_onboarding").list(tenant_id=self.tenant_id, limit=5)
        if not records:
            return None
        rec = sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)[0]
        rd = rec.get("data") or {}
        dept = self._get_department(rd.get("department_id"))
        step_status = rd.get("step_status_json", {})
        steps_with_status = [
            {**step, "status": step_status.get(step["id"], "pending")}
            for step in ONBOARDING_STEPS
        ]
        completed = sum(1 for s in steps_with_status if s["status"] == "complete")
        total_required = sum(1 for s in ONBOARDING_STEPS if s["required"])
        return {
            "onboarding_id": str(rec["id"]),
            "department": dept,
            "steps": steps_with_status,
            "progress_percent": int(completed / len(ONBOARDING_STEPS) * 100),
            "required_complete": sum(1 for s in steps_with_status if s["required"] and s["status"] == "complete"),
            "required_total": total_required,
            "production_ready": completed == len(ONBOARDING_STEPS),
            "completed_at": rd.get("completed_at"),
            "wi_dsps_checklist": rd.get("wi_dsps_checklist", {}),
            "golive_items": WI_DSPS_GOLIVE_CHECKLIST,
        }

    async def complete_step(
        self,
        step_id: str,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        records = self.svc.repo("neris_onboarding").list(tenant_id=self.tenant_id, limit=5)
        if not records:
            raise ValueError("no_onboarding_started")
        rec = sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)[0]
        rd = dict(rec.get("data") or {})
        department_id = rd.get("department_id")

        valid_ids = {s["id"] for s in ONBOARDING_STEPS}
        if step_id not in valid_ids:
            raise ValueError(f"invalid_step: {step_id}")

        # Step-specific validation and side-effects
        await self._process_step(step_id, data, department_id, rd, correlation_id)

        step_status = dict(rd.get("step_status_json", {}))
        step_status[step_id] = "complete"
        rd["step_status_json"] = step_status

        all_required_done = all(
            step_status.get(s["id"]) == "complete"
            for s in ONBOARDING_STEPS if s["required"]
        )
        if all_required_done and not rd.get("completed_at"):
            rd["completed_at"] = datetime.now(timezone.utc).isoformat()
            dept = self._get_department(department_id)
            if dept:
                dept_data = dict(dept.get("data") or {})
                dept_data["status"] = "ready"
                await self.svc.update(
                    table="fire_departments",
                    tenant_id=self.tenant_id,
                    record_id=uuid.UUID(department_id),
                    actor_user_id=self.actor_user_id,
                    patch=dept_data,
                    expected_version=dept.get("version", 1),
                    correlation_id=correlation_id,
                )

        updated = await self.svc.update(
            table="neris_onboarding",
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(str(rec["id"])),
            actor_user_id=self.actor_user_id,
            patch=rd,
            expected_version=rec.get("version", 1),
            correlation_id=correlation_id,
        )
        return updated

    async def _process_step(self, step_id: str, data: dict, department_id: str | None, rd: dict, correlation_id: str | None) -> None:
        dept_uuid = uuid.UUID(department_id) if department_id else None

        if step_id == "department_identity" and dept_uuid:
            dept = self._get_department(department_id)
            if dept:
                dept_data = dict(dept.get("data") or {})
                for field in ("name", "primary_contact_name", "primary_contact_email", "primary_contact_phone"):
                    if data.get(field):
                        dept_data[field] = data[field]
                await self.svc.update(
                    table="fire_departments",
                    tenant_id=self.tenant_id,
                    record_id=dept_uuid,
                    actor_user_id=self.actor_user_id,
                    patch=dept_data,
                    expected_version=dept.get("version", 1),
                    correlation_id=correlation_id,
                )

        elif step_id == "reporting_mode":
            if dept_uuid:
                dept = self._get_department(department_id)
                if dept:
                    dept_data = dict(dept.get("data") or {})
                    dept_data["reporting_mode"] = data.get("reporting_mode", "RMS")
                    await self.svc.update(
                        table="fire_departments",
                        tenant_id=self.tenant_id,
                        record_id=dept_uuid,
                        actor_user_id=self.actor_user_id,
                        patch=dept_data,
                        expected_version=dept.get("version", 1),
                        correlation_id=correlation_id,
                    )
            rd["reporting_mode"] = data.get("reporting_mode", "RMS")

        elif step_id == "stations" and dept_uuid:
            for station in data.get("stations", []):
                await self.svc.create(
                    table="fire_stations",
                    tenant_id=self.tenant_id,
                    actor_user_id=self.actor_user_id,
                    data={"department_id": str(dept_uuid), "name": station.get("name", ""), "address_json": station.get("address", {})},
                    correlation_id=correlation_id,
                )

        elif step_id == "apparatus" and dept_uuid:
            for app in data.get("apparatus", []):
                await self.svc.create(
                    table="fire_apparatus",
                    tenant_id=self.tenant_id,
                    actor_user_id=self.actor_user_id,
                    data={"department_id": str(dept_uuid), "unit_id": app.get("unit_id", ""), "unit_type_code": app.get("unit_type_code", ""), "station_id": app.get("station_id")},
                    correlation_id=correlation_id,
                )

        elif step_id == "personnel" and dept_uuid:
            for p in data.get("personnel", []):
                await self.svc.create(
                    table="fire_personnel",
                    tenant_id=self.tenant_id,
                    actor_user_id=self.actor_user_id,
                    data={"department_id": str(dept_uuid), "name": p.get("name", ""), "role_code": p.get("role_code")},
                    correlation_id=correlation_id,
                )

        elif step_id == "pack_assignment" and dept_uuid:
            active_packs = self.svc.repo("neris_packs").list(tenant_id=self.tenant_id, limit=50)
            active = next((p for p in active_packs if (p.get("data") or {}).get("status") == "active"), None)
            if active:
                dept = self._get_department(department_id)
                if dept:
                    dept_data = dict(dept.get("data") or {})
                    dept_data["neris_pack_id"] = str(active["id"])
                    await self.svc.update(
                        table="fire_departments",
                        tenant_id=self.tenant_id,
                        record_id=dept_uuid,
                        actor_user_id=self.actor_user_id,
                        patch=dept_data,
                        expected_version=dept.get("version", 1),
                        correlation_id=correlation_id,
                    )
            else:
                raise ValueError("no_active_neris_pack")

        elif step_id == "sample_incident":
            # Verify sample incident was validated
            incident_id = data.get("sample_incident_id")
            if not incident_id:
                raise ValueError("sample_incident_id_required")
            inc = self.svc.repo("fire_incidents").get(tenant_id=self.tenant_id, record_id=uuid.UUID(incident_id))
            if not inc or (inc.get("data") or {}).get("status") not in ("validated", "exported"):
                raise ValueError("sample_incident_not_validated")

        elif step_id == "golive_checklist":
            checklist = data.get("checklist", {})
            rd["wi_dsps_checklist"] = checklist

    def _get_department(self, department_id: str | None) -> dict[str, Any] | None:
        if not department_id:
            return None
        try:
            return self.svc.repo("fire_departments").get(tenant_id=self.tenant_id, record_id=uuid.UUID(department_id))
        except Exception:
            return None

    def can_export_production(self) -> bool:
        status = self.get_status()
        if not status:
            return False
        return status.get("production_ready", False)
