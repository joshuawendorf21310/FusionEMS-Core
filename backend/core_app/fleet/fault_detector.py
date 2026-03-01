from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

OBD_FAULT_THRESHOLDS = {
    "coolant_temp_c": {"max": 110, "severity": "critical", "message": "Engine coolant temperature critical ({value}°C). Stop vehicle immediately."},
    "engine_rpm": {"max": 6000, "severity": "warning", "message": "Engine RPM high ({value} RPM)."},
    "battery_voltage": {"min": 11.5, "severity": "warning", "message": "Battery voltage low ({value}V). Check charging system."},
    "fuel_level_pct": {"min": 10, "severity": "warning", "message": "Fuel level critically low ({value}%)."},
    "oil_pressure_kpa": {"min": 100, "severity": "critical", "message": "Oil pressure critically low ({value} kPa). Stop vehicle immediately."},
    "throttle_position_pct": {"max": 99, "severity": "info", "message": "Throttle at maximum ({value}%)."},
    "speed_kmh": {"max": 160, "severity": "warning", "message": "Vehicle speed excessive ({value} km/h)."},
}

IDLE_RPM_MIN = 400
IDLE_RPM_MAX = 900
IDLE_SPEED_MAX_KMH = 2


class FaultDetector:
    def __init__(self, db: Session, publisher: EventPublisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id

    def analyze_obd_reading(self, unit_id: uuid.UUID, obd_payload: dict[str, Any]) -> list[dict[str, Any]]:
        alerts = []
        for pid, thresholds in OBD_FAULT_THRESHOLDS.items():
            value = obd_payload.get(pid)
            if value is None:
                continue
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            triggered = False
            if "max" in thresholds and value > thresholds["max"]:
                triggered = True
            if "min" in thresholds and value < thresholds["min"]:
                triggered = True
            if triggered:
                alerts.append({
                    "unit_id": str(unit_id),
                    "pid": pid,
                    "value": value,
                    "severity": thresholds["severity"],
                    "message": thresholds["message"].format(value=value),
                    "source": "obd_fault_detector",
                    "acknowledged": False,
                    "resolved": False,
                    "detected_at": datetime.now(UTC).isoformat(),
                })

        fault_codes = obd_payload.get("fault_codes", [])
        for code in fault_codes:
            alerts.append({
                "unit_id": str(unit_id),
                "pid": "dtc",
                "value": code,
                "severity": "warning",
                "message": f"DTC fault code detected: {code}",
                "source": "obd_dtc",
                "acknowledged": False,
                "resolved": False,
                "detected_at": datetime.now(UTC).isoformat(),
            })

        rpm = obd_payload.get("engine_rpm")
        speed = obd_payload.get("speed_kmh")
        if rpm is not None and speed is not None:
            try:
                if IDLE_RPM_MIN <= float(rpm) <= IDLE_RPM_MAX and float(speed) <= IDLE_SPEED_MAX_KMH:
                    alerts.append({
                        "unit_id": str(unit_id),
                        "pid": "idle_detection",
                        "value": float(rpm),
                        "severity": "info",
                        "message": f"Vehicle idle detected — RPM {rpm}, speed {speed} km/h.",
                        "source": "idle_detector",
                        "acknowledged": False,
                        "resolved": False,
                        "detected_at": datetime.now(UTC).isoformat(),
                    })
            except (TypeError, ValueError):
                pass

        return alerts

    async def process_and_store(
        self, unit_id: uuid.UUID, obd_payload: dict[str, Any], correlation_id: str | None = None
    ) -> dict[str, Any]:
        alerts = self.analyze_obd_reading(unit_id, obd_payload)
        stored = []
        for alert_data in alerts:
            if alert_data["severity"] in ("critical", "warning"):
                record = await self.svc.create(
                    table="fleet_alerts",
                    tenant_id=self.tenant_id,
                    actor_user_id=self.actor_user_id,
                    data=alert_data,
                    correlation_id=correlation_id,
                )
                stored.append(record)
        return {"unit_id": str(unit_id), "alerts_detected": len(alerts), "alerts_stored": len(stored), "alerts": alerts}
