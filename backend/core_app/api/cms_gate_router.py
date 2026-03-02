from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/cms-gate", tags=["CMS Gate"])

ALLOWED_ROLES = {"founder", "agency_admin", "admin", "dispatcher", "ems"}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


def _compute_cms_score(data: dict[str, Any]) -> dict[str, Any]:
    score = 0
    issues: list[str] = []
    gates: list[dict] = []

    def gate(name: str, passed: bool, weight: int, failure_msg: str) -> None:
        nonlocal score
        gates.append({"gate": name, "passed": passed, "weight": weight})
        if passed:
            score += weight
        else:
            issues.append(failure_msg)

    patient_condition = (data.get("patient_condition") or "").strip()
    gate(
        "patient_condition_provided",
        bool(patient_condition),
        15,
        "Patient condition/chief complaint is required.",
    )

    transport_reason = (data.get("transport_reason") or "").strip()
    gate(
        "transport_reason_provided", bool(transport_reason), 15, "Reason for transport is required."
    )

    origin_address = (data.get("origin_address") or "").strip()
    gate("origin_address_provided", bool(origin_address), 10, "Origin address is required.")

    destination = (data.get("destination_name") or "").strip()
    gate("destination_provided", bool(destination), 10, "Destination facility/address is required.")

    pcs_present = bool(data.get("pcs_on_file") or data.get("pcs_obtained"))
    transport_level = (data.get("transport_level") or "").upper()
    if transport_level in ("ALS", "SCT", "SPECIALTY"):
        gate(
            "pcs_present_for_als",
            pcs_present,
            20,
            "PCS (Physician Certification Statement) required for ALS/Specialty transport.",
        )
    else:
        gate("pcs_present_for_als", True, 20, "")

    necessity_documented = bool(data.get("medical_necessity_documented"))
    gate("necessity_documented", necessity_documented, 15, "Medical necessity must be documented.")

    signature_present = bool(data.get("patient_signature") or data.get("signature_on_file"))
    gate(
        "signature_present",
        signature_present,
        10,
        "Patient signature or signature-on-file required.",
    )

    insurance_present = bool(
        data.get("primary_insurance_id") or data.get("medicare_id") or data.get("medicaid_id")
    )
    gate("insurance_verified", insurance_present, 5, "Insurance information should be provided.")

    free_text = (data.get("transport_reason") or "") + " " + (data.get("patient_condition") or "")
    bs_phrases = [
        "taxi",
        "no ride",
        "no transportation",
        "convenience",
        "prefer not to walk",
        "family refused",
        "doesn't want to",
        "just needs a ride",
    ]
    bs_flag = any(phrase in free_text.lower() for phrase in bs_phrases)
    gate(
        "anti_bs_check",
        not bs_flag,
        0,
        "Transport reason contains language suggesting non-medical necessity ('taxi service' type phrases). Review required.",
    )

    total_weight = sum(g["weight"] for g in gates)
    pct = int(score / total_weight * 100) if total_weight else 0

    hard_block = transport_level in ("ALS", "SCT", "SPECIALTY") and not pcs_present
    hard_block = hard_block or not necessity_documented

    return {
        "score": pct,
        "raw_score": score,
        "max_score": total_weight,
        "passed": pct >= 70 and not hard_block,
        "hard_block": hard_block,
        "issues": issues,
        "gates": gates,
        "bs_flag": bs_flag,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


@router.post("/evaluate")
async def evaluate(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    result = _compute_cms_score(payload)
    correlation_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)
    record = await svc.create(
        table="cms_gate_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "input": payload},
        correlation_id=correlation_id,
    )
    return {**result, "record_id": str(record["id"])}


@router.post("/cases/{case_id}/evaluate")
async def evaluate_for_case(
    case_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    case = svc.repo("cases").get(tenant_id=current.tenant_id, record_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    result = _compute_cms_score(payload)
    correlation_id = getattr(request.state, "correlation_id", None)
    record = await svc.create(
        table="cms_gate_results",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**result, "case_id": str(case_id), "input": payload},
        correlation_id=correlation_id,
    )
    case_data = dict(case.get("data") or {})
    case_data["cms_gate_passed"] = result["passed"]
    case_data["cms_gate_score"] = result["score"]
    case_data["cms_gate_result"] = str(record["id"])
    await svc.update(
        table="cases",
        tenant_id=current.tenant_id,
        record_id=case_id,
        actor_user_id=current.user_id,
        patch=case_data,
        expected_version=case.get("version", 1),
        correlation_id=correlation_id,
    )
    return {**result, "record_id": str(record["id"]), "case_id": str(case_id)}


@router.get("/cases/{case_id}/result")
async def get_gate_result(
    case_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    all_results = svc.repo("cms_gate_results").list(tenant_id=current.tenant_id, limit=100)
    result = next(
        (r for r in reversed(all_results) if (r.get("data") or {}).get("case_id") == str(case_id)),
        None,
    )
    if not result:
        raise HTTPException(status_code=404, detail="No CMS gate result for this case")
    return result
