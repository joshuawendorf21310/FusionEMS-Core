from __future__ import annotations

from typing import Any
from dataclasses import dataclass


@dataclass
class WorkflowBlock:
    block_id: str
    block_type: str
    label: str
    required: bool
    mode_applicability: list[str]
    order: int
    prompts: list[str]
    required_fields: list[str]
    conditional_rules: list[dict[str, Any]]
    quick_fill_options: list[str]


BLS_BLOCKS: list[WorkflowBlock] = [
    WorkflowBlock(
        block_id="dispatch",
        block_type="dispatch",
        label="Dispatch",
        required=True,
        mode_applicability=["bls"],
        order=1,
        prompts=["Enter CAD info or import from dispatch", "Record all times carefully"],
        required_fields=["dispatch.incident_number", "dispatch.psap_call_time"],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="consent",
        block_type="consent",
        label="Consent",
        required=True,
        mode_applicability=["bls"],
        order=2,
        prompts=["Document patient consent type", "For refusals: confirm capacity, explain risks, obtain signature"],
        required_fields=["consent.consent_type"],
        conditional_rules=[],
        quick_fill_options=["Informed", "Implied", "Refusal", "Guardian"],
    ),
    WorkflowBlock(
        block_id="primary_assessment",
        block_type="assessment",
        label="Primary Assessment",
        required=True,
        mode_applicability=["bls"],
        order=3,
        prompts=["Document chief complaint", "ABCDE primary survey"],
        required_fields=["assessments[0].chief_complaint"],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="vitals",
        block_type="vitals",
        label="Vitals",
        required=True,
        mode_applicability=["bls"],
        order=4,
        prompts=["Record initial vitals with timestamp", "Reassess after interventions"],
        required_fields=["vitals"],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="medications",
        block_type="medications",
        label="Medications",
        required=False,
        mode_applicability=["bls"],
        order=5,
        prompts=["Document all meds given and prior meds"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="procedures",
        block_type="procedures",
        label="Procedures",
        required=False,
        mode_applicability=["bls"],
        order=6,
        prompts=["Document all procedures with time and attempts"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="secondary_assessment",
        block_type="assessment",
        label="Secondary Assessment",
        required=False,
        mode_applicability=["bls"],
        order=7,
        prompts=["Secondary survey findings"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="disposition",
        block_type="disposition",
        label="Disposition",
        required=True,
        mode_applicability=["bls"],
        order=8,
        prompts=["Document transport decision", "Record destination and mode"],
        required_fields=["disposition.patient_disposition_code"],
        conditional_rules=[],
        quick_fill_options=["Transport", "Refusal", "Treat No Transport", "DOA", "Cancelled"],
    ),
    WorkflowBlock(
        block_id="narrative",
        block_type="narrative",
        label="Narrative",
        required=True,
        mode_applicability=["bls"],
        order=9,
        prompts=["Write or generate narrative", "Review for completeness"],
        required_fields=["narrative"],
        conditional_rules=[],
        quick_fill_options=[],
    ),
]

ACLS_BLOCKS: list[WorkflowBlock] = [
    WorkflowBlock(
        block_id=b.block_id,
        block_type=b.block_type,
        label=b.label,
        required=b.required,
        mode_applicability=["acls"],
        order=b.order,
        prompts=b.prompts,
        required_fields=b.required_fields,
        conditional_rules=b.conditional_rules,
        quick_fill_options=b.quick_fill_options,
    )
    for b in BLS_BLOCKS
] + [
    WorkflowBlock(
        block_id="acls_code_timeline",
        block_type="acls",
        label="ACLS Code Timeline",
        required=True,
        mode_applicability=["acls"],
        order=5,
        prompts=["Record code start time", "Document each intervention with timestamp", "ROSC or termination time required"],
        required_fields=["acls.code_start_time", "acls.initial_rhythm"],
        conditional_rules=[],
        quick_fill_options=["VF", "VT", "PEA", "Asystole", "Normal Sinus"],
    ),
    WorkflowBlock(
        block_id="rhythm_capture",
        block_type="acls",
        label="Rhythm Capture",
        required=False,
        mode_applicability=["acls"],
        order=6,
        prompts=["Attach rhythm strip image", "Link to vital entry"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
]

CCT_BLOCKS: list[WorkflowBlock] = [
    WorkflowBlock(
        block_id=b.block_id,
        block_type=b.block_type,
        label=b.label,
        required=b.required,
        mode_applicability=["cct"],
        order=b.order,
        prompts=b.prompts,
        required_fields=b.required_fields,
        conditional_rules=b.conditional_rules,
        quick_fill_options=b.quick_fill_options,
    )
    for b in BLS_BLOCKS
] + [
    WorkflowBlock(
        block_id="cct_transfer_docs",
        block_type="cct",
        label="CCT Transfer Documents",
        required=False,
        mode_applicability=["cct"],
        order=2,
        prompts=["Ingest transfer paperwork", "Document prior meds/procedures as 'prior to our care'"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="cct_drips",
        block_type="cct",
        label="CCT Active Drips",
        required=False,
        mode_applicability=["cct"],
        order=5,
        prompts=["Document all active infusions", "Record drug, concentration, rate, site"],
        required_fields=["cct.drips"],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="cct_vent_settings",
        block_type="cct",
        label="CCT Vent Settings",
        required=False,
        mode_applicability=["cct"],
        order=6,
        prompts=["Capture vent screen or enter settings manually", "Mode, FiO2, PEEP, tidal volume, rate"],
        required_fields=["cct.vent_settings"],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="cct_hemodynamics",
        block_type="cct",
        label="CCT Hemodynamics",
        required=False,
        mode_applicability=["cct"],
        order=7,
        prompts=["Trend hemodynamic values throughout transport"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
]

HEMS_BLOCKS: list[WorkflowBlock] = [
    WorkflowBlock(
        block_id=b.block_id,
        block_type=b.block_type,
        label=b.label,
        required=b.required,
        mode_applicability=["hems"],
        order=b.order,
        prompts=b.prompts,
        required_fields=b.required_fields,
        conditional_rules=b.conditional_rules,
        quick_fill_options=b.quick_fill_options,
    )
    for b in BLS_BLOCKS
] + [
    WorkflowBlock(
        block_id="hems_timeline",
        block_type="hems",
        label="HEMS Flight Timeline",
        required=True,
        mode_applicability=["hems"],
        order=1,
        prompts=["Record wheels up/wheels down times", "Mission number required"],
        required_fields=["hems.wheels_up_time", "hems.wheels_down_time", "hems.mission_number"],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="hems_weight_dosing",
        block_type="hems",
        label="HEMS Weight-Based Dosing",
        required=False,
        mode_applicability=["hems"],
        order=5,
        prompts=["Use weight-based dosing calculator", "Patient weight required for peds dosing"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
    WorkflowBlock(
        block_id="hems_handoff",
        block_type="hems",
        label="HEMS Handoff Summary",
        required=False,
        mode_applicability=["hems"],
        order=9,
        prompts=["Generate scene/handoff summary for receiving team"],
        required_fields=[],
        conditional_rules=[],
        quick_fill_options=[],
    ),
]

PALS_BLOCK: WorkflowBlock = WorkflowBlock(
    block_id="pals_prompts",
    block_type="pals",
    label="PALS Pediatric Prompts",
    required=False,
    mode_applicability=["all"],
    order=3,
    prompts=[
        "Pediatric patient detected",
        "Use weight-based dosing",
        "PALS protocol prompts active",
        "Broselow tape color?",
    ],
    required_fields=["patient.weight_kg"],
    conditional_rules=[
        {"condition": "patient_age_lt_12", "action": "require", "target_field": "patient.weight_kg"}
    ],
    quick_fill_options=[],
)

_MODE_BLOCK_MAP: dict[str, list[WorkflowBlock]] = {
    "bls": BLS_BLOCKS,
    "acls": ACLS_BLOCKS,
    "cct": CCT_BLOCKS,
    "hems": HEMS_BLOCKS,
    "fire": BLS_BLOCKS,
}


def get_blocks_for_mode(mode: str, patient_age: int | None = None) -> list[WorkflowBlock]:
    blocks = list(_MODE_BLOCK_MAP.get(mode, BLS_BLOCKS))
    if patient_age is not None and patient_age < 12:
        blocks = [b for b in blocks if b.block_id != "pals_prompts"]
        blocks.append(PALS_BLOCK)
    return sorted(blocks, key=lambda b: b.order)


def get_required_fields_for_mode(mode: str) -> list[str]:
    blocks = get_blocks_for_mode(mode)
    fields: list[str] = []
    for block in blocks:
        if block.required:
            fields.extend(block.required_fields)
    return fields


def check_conditional_rules(chart: dict[str, Any]) -> list[dict[str, Any]]:
    triggered: list[dict[str, Any]] = []
    all_blocks: list[WorkflowBlock] = []
    for blocks in _MODE_BLOCK_MAP.values():
        for b in blocks:
            if b not in all_blocks:
                all_blocks.append(b)
    if PALS_BLOCK not in all_blocks:
        all_blocks.append(PALS_BLOCK)

    patient = chart.get("patient", {})
    dob_str = patient.get("dob", "")
    patient_age: int | None = None
    if dob_str:
        try:
            from datetime import date
            dob = date.fromisoformat(str(dob_str)[:10])
            today = date.today()
            patient_age = (today - dob).days // 365
        except (ValueError, TypeError):
            pass

    for block in all_blocks:
        for rule in block.conditional_rules:
            condition = rule.get("condition", "")
            result = False
            if condition == "patient_age_lt_12":
                result = patient_age is not None and patient_age < 12
            triggered.append({
                "block_id": block.block_id,
                "rule": rule,
                "triggered": result,
            })

    return triggered
