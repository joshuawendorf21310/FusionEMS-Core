from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ChartMode(str, Enum):
    BLS = "bls"
    ACLS = "acls"
    CCT = "cct"
    HEMS = "hems"
    FIRE = "fire"


class ChartStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    PENDING_QA = "pending_qa"
    SUBMITTED = "submitted"
    LOCKED = "locked"
    CANCELLED = "cancelled"


class SyncStatus(str, Enum):
    LOCAL_ONLY = "local_only"
    SYNCED = "synced"
    CONFLICT = "conflict"
    PENDING_SYNC = "pending_sync"


@dataclass
class PatientDemographics:
    first_name: str = ""
    last_name: str = ""
    dob: str = ""
    gender: str = ""
    race: str = ""
    ssn_last4: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phone: str = ""
    mrn: str = ""
    insurance_id: str = ""
    insurance_group: str = ""
    insurance_payer: str = ""
    weight_kg: float | None = None
    height_cm: float | None = None


@dataclass
class ConsentRecord:
    consent_type: str = ""
    consented_by: str = ""
    consent_time: str = ""
    refusal_reason: str = ""
    capacity_confirmed: bool = False
    risks_explained: bool = False
    signature_attachment_id: str = ""


@dataclass
class DispatchInfo:
    incident_number: str = ""
    psap_call_time: str = ""
    unit_notified_time: str = ""
    unit_enroute_time: str = ""
    arrived_scene_time: str = ""
    patient_contact_time: str = ""
    departed_scene_time: str = ""
    arrived_destination_time: str = ""
    transfer_of_care_time: str = ""
    call_type_code: str = ""
    complaint_reported: str = ""
    priority_level: str = ""
    cad_incident_id: str = ""
    responding_unit: str = ""
    crew_members: list[str] = field(default_factory=list)


@dataclass
class VitalSet:
    vital_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recorded_at: str = ""
    recorded_by: str = ""
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    spo2: float | None = None
    etco2: float | None = None
    glucose: float | None = None
    gcs_eye: int | None = None
    gcs_verbal: int | None = None
    gcs_motor: int | None = None
    gcs_total: int | None = None
    temperature_c: float | None = None
    pain_scale: int | None = None
    pupils_left: str = ""
    pupils_right: str = ""
    skin_color: str = ""
    skin_temp: str = ""
    skin_moisture: str = ""
    rhythm: str = ""
    rhythm_attachment_id: str = ""
    weight_kg: float | None = None


@dataclass
class MedicationAdmin:
    med_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    medication_name: str = ""
    dose: str = ""
    dose_unit: str = ""
    route: str = ""
    time_given: str = ""
    given_by: str = ""
    indication: str = ""
    lot_number: str = ""
    expiration: str = ""
    prior_to_our_care: bool = False
    attachment_id: str = ""


@dataclass
class ProcedurePerformed:
    proc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    procedure_name: str = ""
    procedure_code: str = ""
    time_performed: str = ""
    performed_by: str = ""
    attempts: int = 1
    successful: bool = True
    complications: str = ""
    confirmation_method: str = ""
    prior_to_our_care: bool = False
    attachment_id: str = ""


@dataclass
class AssessmentBlock:
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assessment_type: str = "primary"
    time: str = ""
    performed_by: str = ""
    chief_complaint: str = ""
    hpi: str = ""
    history: str = ""
    allergies: list[str] = field(default_factory=list)
    medications_home: list[str] = field(default_factory=list)
    airway_status: str = ""
    breathing_status: str = ""
    circulation_status: str = ""
    neuro_status: str = ""
    trauma_findings: dict[str, Any] = field(default_factory=dict)
    medical_findings: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class DispositionInfo:
    patient_disposition_code: str = ""
    transport_disposition: str = ""
    destination_name: str = ""
    destination_id: str = ""
    room_number: str = ""
    transferred_to_name: str = ""
    transport_mode: str = ""
    level_of_care: str = ""
    reason_not_transported: str = ""
    signature_attachment_id: str = ""


@dataclass
class ACLSBlock:
    code_start_time: str = ""
    rosc_time: str = ""
    termination_time: str = ""
    initial_rhythm: str = ""
    final_rhythm: str = ""
    defibrillation_events: list[dict[str, Any]] = field(default_factory=list)
    pacing_events: list[dict[str, Any]] = field(default_factory=list)
    total_shocks: int = 0


@dataclass
class CCTBlock:
    drips: list[dict[str, Any]] = field(default_factory=list)
    vent_settings: dict[str, Any] = field(default_factory=dict)
    infusion_programs: list[dict[str, Any]] = field(default_factory=list)
    hemodynamics_trend: list[dict[str, Any]] = field(default_factory=list)
    transfer_source_facility: str = ""
    transfer_source_unit: str = ""
    receiving_facility: str = ""


@dataclass
class HEMSBlock:
    wheels_up_time: str = ""
    wheels_down_time: str = ""
    mission_number: str = ""
    aircraft_id: str = ""
    lz_coords: dict[str, Any] = field(default_factory=dict)
    flight_crew: list[str] = field(default_factory=list)
    flight_time_minutes: float | None = None
    handoff_summary: str = ""


@dataclass
class ProvenanceRecord:
    field_name: str = ""
    value: Any = None
    source_type: str = "manual"
    source_attachment_id: str = ""
    confidence: float = 1.0
    confirmed_by: str = ""
    confirmed_at: str = ""
    bounding_box: dict[str, Any] = field(default_factory=dict)


def _build_dataclass(cls, raw: dict) -> object:
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name in raw:
            kwargs[f.name] = raw[f.name]
        elif f.default is not dataclasses.MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not dataclasses.MISSING:
            kwargs[f.name] = f.default_factory()
        else:
            kwargs[f.name] = None
    return cls(**kwargs)


@dataclass
class Chart:
    chart_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    resource_pack_id: str | None = None
    chart_mode: str = ChartMode.BLS.value
    chart_status: str = ChartStatus.DRAFT.value
    sync_status: str = SyncStatus.PENDING_SYNC.value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = ""
    last_modified_by: str = ""
    patient: PatientDemographics = field(default_factory=PatientDemographics)
    consent: ConsentRecord = field(default_factory=ConsentRecord)
    dispatch: DispatchInfo = field(default_factory=DispatchInfo)
    vitals: list[VitalSet] = field(default_factory=list)
    medications: list[MedicationAdmin] = field(default_factory=list)
    procedures: list[ProcedurePerformed] = field(default_factory=list)
    assessments: list[AssessmentBlock] = field(default_factory=list)
    disposition: DispositionInfo = field(default_factory=DispositionInfo)
    acls: ACLSBlock | None = None
    cct: CCTBlock | None = None
    hems: HEMSBlock | None = None
    narrative: str = ""
    attachments: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    completeness_score: float = 0.0
    completeness_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Chart":
        c = cls.__new__(cls)
        c.chart_id = d.get("chart_id", str(uuid.uuid4()))
        c.tenant_id = d.get("tenant_id", "")
        c.resource_pack_id = d.get("resource_pack_id")
        c.chart_mode = d.get("chart_mode", ChartMode.BLS.value)
        c.chart_status = d.get("chart_status", ChartStatus.DRAFT.value)
        c.sync_status = d.get("sync_status", SyncStatus.PENDING_SYNC.value)
        c.created_at = d.get("created_at", datetime.now(timezone.utc).isoformat())
        c.updated_at = d.get("updated_at", datetime.now(timezone.utc).isoformat())
        c.created_by = d.get("created_by", "")
        c.last_modified_by = d.get("last_modified_by", "")

        c.patient = _build_dataclass(PatientDemographics, d.get("patient", {})) if isinstance(d.get("patient"), dict) else PatientDemographics()
        c.consent = _build_dataclass(ConsentRecord, d.get("consent", {})) if isinstance(d.get("consent"), dict) else ConsentRecord()
        c.dispatch = _build_dataclass(DispatchInfo, d.get("dispatch", {})) if isinstance(d.get("dispatch"), dict) else DispatchInfo()
        c.disposition = _build_dataclass(DispositionInfo, d.get("disposition", {})) if isinstance(d.get("disposition"), dict) else DispositionInfo()

        c.vitals = [
            _build_dataclass(VitalSet, vs)
            for vs in d.get("vitals", [])
            if isinstance(vs, dict)
        ]
        c.medications = [
            _build_dataclass(MedicationAdmin, m)
            for m in d.get("medications", [])
            if isinstance(m, dict)
        ]
        c.procedures = [
            _build_dataclass(ProcedurePerformed, pr)
            for pr in d.get("procedures", [])
            if isinstance(pr, dict)
        ]
        c.assessments = [
            _build_dataclass(AssessmentBlock, a)
            for a in d.get("assessments", [])
            if isinstance(a, dict)
        ]
        c.provenance = [
            _build_dataclass(ProvenanceRecord, pr)
            for pr in d.get("provenance", [])
            if isinstance(pr, dict)
        ]

        acls_d = d.get("acls")
        c.acls = _build_dataclass(ACLSBlock, acls_d) if isinstance(acls_d, dict) else None
        cct_d = d.get("cct")
        c.cct = _build_dataclass(CCTBlock, cct_d) if isinstance(cct_d, dict) else None
        hems_d = d.get("hems")
        c.hems = _build_dataclass(HEMSBlock, hems_d) if isinstance(hems_d, dict) else None

        c.narrative = d.get("narrative", "")
        c.attachments = d.get("attachments", [])
        c.completeness_score = d.get("completeness_score", 0.0)
        c.completeness_issues = d.get("completeness_issues", [])
        return c
