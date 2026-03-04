from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TransportMode(str, Enum):
    GROUND_ALS = "ground_als"
    GROUND_BLS = "ground_bls"
    GROUND_CCT = "ground_cct"
    HELICOPTER = "helicopter"
    FIXED_WING = "fixed_wing"
    IFT_ALS = "ift_als"
    IFT_BLS = "ift_bls"
    IFT_CCT = "ift_cct"
    FIRE_EMS = "fire_ems"


class ServiceLevel(str, Enum):
    BLS_EMERGENCY = "A0427"
    BLS_NON_EMERGENCY = "A0428"
    ALS_EMERGENCY = "A0429"
    ALS_NON_EMERGENCY = "A0426"
    ALS2 = "A0433"
    SCT = "A0434"
    ROTARY_WING = "A0431"
    FIXED_WING = "A0430"


HCPCS_MAP: dict[TransportMode, ServiceLevel] = {
    TransportMode.GROUND_BLS: ServiceLevel.BLS_EMERGENCY,
    TransportMode.GROUND_ALS: ServiceLevel.ALS_EMERGENCY,
    TransportMode.GROUND_CCT: ServiceLevel.SCT,
    TransportMode.HELICOPTER: ServiceLevel.ROTARY_WING,
    TransportMode.FIXED_WING: ServiceLevel.FIXED_WING,
    TransportMode.IFT_ALS: ServiceLevel.ALS_NON_EMERGENCY,
    TransportMode.IFT_BLS: ServiceLevel.BLS_NON_EMERGENCY,
    TransportMode.IFT_CCT: ServiceLevel.SCT,
    TransportMode.FIRE_EMS: ServiceLevel.ALS_EMERGENCY,
}


@dataclass
class MileageCharge:
    loaded_miles: float
    rate_per_mile: float
    hcpcs: str = "A0425"

    @property
    def total(self) -> float:
        return round(self.loaded_miles * self.rate_per_mile, 2)


@dataclass
class TransportBillingRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    patient_id: str = ""
    incident_id: str = ""
    transport_mode: TransportMode = TransportMode.GROUND_ALS
    service_level: ServiceLevel = ServiceLevel.ALS_EMERGENCY
    service_date: str = ""
    pickup_address: str = ""
    dropoff_address: str = ""
    loaded_miles: float = 0.0
    base_rate: float = 0.0
    mileage_rate: float = 0.0
    supplies: list[dict] = field(default_factory=list)
    icd10_codes: list[str] = field(default_factory=list)
    pcs_on_file: bool = False
    signature_on_file: bool = False
    phi_partition: str = "clinical"
    audit_trail: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def compute_total(self) -> float:
        mileage_total = round(self.loaded_miles * self.mileage_rate, 2)
        supplies_total = sum(s.get("amount", 0) for s in self.supplies)
        return round(self.base_rate + mileage_total + supplies_total, 2)

    def to_claim_lines(self) -> list[dict]:
        lines = [
            {
                "line_number": 1,
                "hcpcs": self.service_level.value,
                "description": f"Transport - {self.transport_mode.value}",
                "units": 1,
                "amount": self.base_rate,
                "icd10_pointer": "1",
            },
        ]
        if self.loaded_miles > 0:
            mileage = MileageCharge(
                loaded_miles=self.loaded_miles,
                rate_per_mile=self.mileage_rate,
            )
            lines.append({
                "line_number": 2,
                "hcpcs": mileage.hcpcs,
                "description": f"Loaded mileage ({self.loaded_miles} mi)",
                "units": self.loaded_miles,
                "amount": mileage.total,
                "icd10_pointer": "1",
            })
        for i, supply in enumerate(self.supplies, start=3):
            lines.append({
                "line_number": i,
                "hcpcs": supply.get("hcpcs", "A0998"),
                "description": supply.get("description", "Supply"),
                "units": supply.get("units", 1),
                "amount": supply.get("amount", 0),
                "icd10_pointer": "1",
            })
        return lines

    def add_audit_entry(self, action: str, actor: str, detail: str = "") -> None:
        self.audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor,
            "detail": detail,
        })


class TransportBillingEngine:
    @staticmethod
    def create_record(
        tenant_id: str,
        patient_id: str,
        incident_id: str,
        transport_mode: TransportMode,
        service_date: str,
        pickup: str,
        dropoff: str,
        loaded_miles: float,
        base_rate: float,
        mileage_rate: float,
        icd10_codes: Optional[list[str]] = None,
        actor: str = "system",
    ) -> TransportBillingRecord:
        service_level = HCPCS_MAP.get(transport_mode, ServiceLevel.ALS_EMERGENCY)
        record = TransportBillingRecord(
            tenant_id=tenant_id,
            patient_id=patient_id,
            incident_id=incident_id,
            transport_mode=transport_mode,
            service_level=service_level,
            service_date=service_date,
            pickup_address=pickup,
            dropoff_address=dropoff,
            loaded_miles=loaded_miles,
            base_rate=base_rate,
            mileage_rate=mileage_rate,
            icd10_codes=icd10_codes or [],
            phi_partition="clinical" if transport_mode == TransportMode.HELICOPTER else "transport",
        )
        record.add_audit_entry("created", actor, f"Transport mode: {transport_mode.value}")
        return record

    @staticmethod
    def validate_for_submission(record: TransportBillingRecord) -> list[str]:
        errors = []
        if not record.tenant_id:
            errors.append("tenant_id is required")
        if not record.patient_id:
            errors.append("patient_id is required")
        if not record.icd10_codes:
            errors.append("At least one ICD-10 code is required")
        if record.loaded_miles <= 0 and record.transport_mode != TransportMode.FIRE_EMS:
            errors.append("Loaded miles must be positive for transport claims")
        if not record.pcs_on_file and record.transport_mode in (
            TransportMode.IFT_ALS, TransportMode.IFT_BLS, TransportMode.IFT_CCT
        ):
            errors.append("PCS (Physician Certification Statement) is required for IFT")
        if not record.signature_on_file:
            errors.append("Patient or authorized representative signature is required")
        return errors
