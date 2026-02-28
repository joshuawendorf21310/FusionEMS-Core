from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core_app.database import get_db
from core_app.repositories.domination_repository import DominationRepository

router = APIRouter(prefix="/api/v1/kitlink/compliance", tags=["kitlink-compliance"])

_MANDATORY_ITEMS = [
    "FIRE_EXT_1", "FIRE_EXT_2", "LIGHTS", "O2", "SUCTION", "AED",
    "SPINE_BOARD", "JUMP_BAG", "NARC_BOX", "DRUG_BOX",
]

_WI_TRANS_309_V1 = {
    "pack_key": "WI_TRANS_309_V1",
    "version": "1",
    "state": "WI",
    "title": "Wisconsin Trans 309 Compliance Pack v1",
    "unit_profiles": ["EMT", "AEMT", "PARAMEDIC"],
    "rules": [
        {"rule_id": "NO_EXPIRED_MEDS_FLUIDS", "type": "hard_fail", "description": "No expired medications or IV fluids"},
        {"rule_id": "MANDATORY_PRESENCE_10", "type": "required", "description": "10 mandatory equipment items must be present"},
    ],
    "check_templates": _MANDATORY_ITEMS,
}

_WI_TRANS_309_V2 = {
    "pack_key": "WI_TRANS_309_V2",
    "version": "2",
    "state": "WI",
    "title": "Wisconsin Trans 309 Compliance Pack v2",
    "unit_profiles": ["EMT", "AEMT", "PARAMEDIC"],
    "rules": [
        {"rule_id": "NO_EXPIRED_MEDS_FLUIDS", "type": "hard_fail", "description": "No expired medications or IV fluids"},
        {"rule_id": "MANDATORY_PRESENCE_10", "type": "required", "description": "10 mandatory equipment items must be present"},
        {"rule_id": "NARC_SEAL_INTACT", "type": "required", "description": "Narcotics seal must be intact and verified"},
        {"rule_id": "CALIBRATION_CURRENT", "type": "warning", "description": "All monitoring equipment calibration current"},
    ],
    "check_templates": _MANDATORY_ITEMS,
}

_BUILTIN_PACKS = {"WI_TRANS_309_V1": _WI_TRANS_309_V1, "WI_TRANS_309_V2": _WI_TRANS_309_V2}


def _repo(db: Session) -> DominationRepository:
    return DominationRepository(db)


# ---------------------------------------------------------------------------
# Compliance Packs
# ---------------------------------------------------------------------------

@router.get("/packs")
def list_packs(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    stored = repo.list("compliance_packs", tid)
    active_keys = {r["data"].get("pack_key") for r in stored if r["data"].get("active")}
    result = []
    for key, pack in _BUILTIN_PACKS.items():
        result.append({**pack, "active": key in active_keys})
    return {"packs": result}


@router.post("/packs/activate")
def activate_pack(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    pack_key = payload.get("pack_key")
    if pack_key not in _BUILTIN_PACKS:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_key}' not found")
    pack_data = _BUILTIN_PACKS[pack_key]
    stored = repo.list("compliance_packs", tid)
    existing = next((r for r in stored if r["data"].get("pack_key") == pack_key), None)
    if existing:
        repo.update("compliance_packs", tid, existing["id"], {**existing["data"], "active": True, "activated_at": datetime.now(timezone.utc).isoformat()})
        return {"pack_key": pack_key, "status": "activated", "id": str(existing["id"])}
    row = repo.create("compliance_packs", tid, {
        **pack_data,
        "active": True,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "unit_profile": payload.get("unit_profile", "PARAMEDIC"),
    })
    for item_id in pack_data["check_templates"]:
        repo.create("compliance_check_templates", tid, {
            "pack_key": pack_key,
            "check_id": item_id,
            "label": item_id.replace("_", " ").title(),
            "type": "presence",
        })
    return {"pack_key": pack_key, "status": "activated", "id": str(row["id"])}


# ---------------------------------------------------------------------------
# Inspections
# ---------------------------------------------------------------------------

@router.post("/inspections")
def create_inspection(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.create("compliance_inspections", tid, {
        **payload,
        "status": "in_progress",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": str(row["id"]), "status": "in_progress"}


@router.post("/inspections/{inspection_id}/submit")
def submit_inspection(inspection_id: str, payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("compliance_inspections", tid)
    inspection = next((r for r in rows if str(r["id"]) == inspection_id), None)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    responses = payload.get("responses", {})
    hard_fail = False
    warnings = []
    findings = []

    if responses.get("EXPIRATION_SWEEP") is False or responses.get("EXPIRATION_SWEEP") == "fail":
        hard_fail = True
        f = repo.create("compliance_findings", tid, {
            "inspection_id": inspection_id,
            "rule_id": "NO_EXPIRED_MEDS_FLUIDS",
            "severity": "hard_fail",
            "description": "Expired medications or IV fluids found",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        findings.append({"id": str(f["id"]), "rule_id": "NO_EXPIRED_MEDS_FLUIDS", "severity": "hard_fail"})

    for item_id in _MANDATORY_ITEMS:
        if responses.get(item_id) is False:
            f = repo.create("compliance_findings", tid, {
                "inspection_id": inspection_id,
                "rule_id": "MANDATORY_PRESENCE_10",
                "check_id": item_id,
                "severity": "fail",
                "description": f"Mandatory item missing: {item_id}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            findings.append({"id": str(f["id"]), "rule_id": item_id, "severity": "fail"})

    narc_seal = responses.get("NARC_SEAL_INTACT")
    if narc_seal is False:
        w = repo.create("compliance_findings", tid, {
            "inspection_id": inspection_id,
            "rule_id": "NARC_SEAL_INTACT",
            "severity": "warning",
            "description": "Narcotics seal not verified",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        warnings.append({"id": str(w["id"]), "rule_id": "NARC_SEAL_INTACT"})

    if hard_fail:
        result_status = "fail"
    elif findings:
        result_status = "fail"
    elif warnings:
        result_status = "pass_with_warnings"
    else:
        result_status = "pass"

    repo.update("compliance_inspections", tid, uuid.UUID(inspection_id), {
        **inspection["data"],
        "status": "complete",
        "result_status": result_status,
        "hard_fail": hard_fail,
        "finding_count": len(findings),
        "warning_count": len(warnings),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "responses": responses,
    })

    return {
        "inspection_id": inspection_id,
        "result_status": result_status,
        "hard_fail": hard_fail,
        "findings": findings,
        "warnings": warnings,
    }


@router.get("/inspections")
def list_inspections(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("compliance_inspections", tid)
    return [{"id": str(r["id"]), "data": r["data"]} for r in rows]


@router.get("/inspections/{inspection_id}")
def get_inspection(inspection_id: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("compliance_inspections", tid)
    inspection = next((r for r in rows if str(r["id"]) == inspection_id), None)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return {"id": inspection_id, "data": inspection["data"]}


@router.get("/inspections/{inspection_id}/findings")
def get_inspection_findings(inspection_id: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("compliance_findings", tid)
    findings = [r for r in rows if r["data"].get("inspection_id") == inspection_id]
    return [{"id": str(r["id"]), "data": r["data"]} for r in findings]


# ---------------------------------------------------------------------------
# Compliance Reports
# ---------------------------------------------------------------------------

@router.get("/reports/fleet-score")
def fleet_score(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("compliance_inspections", tid)
    completed = [r for r in rows if r["data"].get("status") == "complete"]
    if not completed:
        return {"fleet_score": None, "inspections_scored": 0}
    passes = sum(1 for r in completed if r["data"].get("result_status") == "pass")
    score = round(passes / len(completed) * 100, 1)
    return {"fleet_score": score, "inspections_scored": len(completed), "pass_count": passes}


@router.get("/reports/inspection-ready")
def inspection_ready(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    inspections = repo.list("compliance_inspections", tid)
    recent_by_unit: dict[str, dict] = {}
    for r in inspections:
        uid = r["data"].get("unit_id", "unknown")
        existing = recent_by_unit.get(uid)
        if not existing or r["data"].get("submitted_at", "") > existing["data"].get("submitted_at", ""):
            recent_by_unit[uid] = r
    result = []
    for uid, r in recent_by_unit.items():
        result.append({
            "unit_id": uid,
            "last_inspection": r["data"].get("submitted_at"),
            "result_status": r["data"].get("result_status"),
            "inspection_ready": r["data"].get("result_status") in ("pass", "pass_with_warnings"),
        })
    return {"units": result}


# ---------------------------------------------------------------------------
# 1-Day Go-Live Wizard
# ---------------------------------------------------------------------------

_WIZARD_STEPS = [
    "choose_compliance_pack",
    "unit_setup",
    "formulary_quick_setup",
    "load_starter_templates",
    "create_unit_layout",
    "generate_marker_sheets",
    "test_scan",
    "enable_inspection_mode",
    "go_live",
]


@router.post("/wizard/step")
def wizard_step(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    step = payload.get("step")
    if step not in _WIZARD_STEPS:
        raise HTTPException(status_code=400, detail=f"Invalid step '{step}'. Valid steps: {_WIZARD_STEPS}")

    rows = repo.list("kitlink_wizard_state", tid)
    existing = rows[0] if rows else None

    if existing:
        steps_completed = existing["data"].get("steps_completed", [])
        if step not in steps_completed:
            steps_completed.append(step)
        go_live_complete = all(s in steps_completed for s in _WIZARD_STEPS)
        repo.update("kitlink_wizard_state", tid, existing["id"], {
            **existing["data"],
            "steps_completed": steps_completed,
            "go_live_complete": go_live_complete,
            "last_step": step,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        })
        state_id = str(existing["id"])
    else:
        steps_completed = [step]
        go_live_complete = len(_WIZARD_STEPS) == 1
        row = repo.create("kitlink_wizard_state", tid, {
            "steps_completed": steps_completed,
            "go_live_complete": go_live_complete,
            "last_step": step,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "step_data": {step: payload.get("data", {})},
        })
        state_id = str(row["id"])

    remaining = [s for s in _WIZARD_STEPS if s not in steps_completed]
    next_step = remaining[0] if remaining else None

    return {
        "state_id": state_id,
        "step_completed": step,
        "steps_completed": steps_completed,
        "next_step": next_step,
        "go_live_complete": go_live_complete,
        "progress": f"{len(steps_completed)}/{len(_WIZARD_STEPS)}",
    }


@router.get("/wizard/state")
def wizard_state(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("kitlink_wizard_state", tid)
    if not rows:
        return {
            "started": False,
            "steps_completed": [],
            "go_live_complete": False,
            "next_step": _WIZARD_STEPS[0],
            "progress": f"0/{len(_WIZARD_STEPS)}",
        }
    state = rows[0]
    steps_completed = state["data"].get("steps_completed", [])
    remaining = [s for s in _WIZARD_STEPS if s not in steps_completed]
    return {
        "started": True,
        "state_id": str(state["id"]),
        "steps_completed": steps_completed,
        "go_live_complete": state["data"].get("go_live_complete", False),
        "next_step": remaining[0] if remaining else None,
        "all_steps": _WIZARD_STEPS,
        "progress": f"{len(steps_completed)}/{len(_WIZARD_STEPS)}",
    }
