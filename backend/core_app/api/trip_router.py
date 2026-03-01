from __future__ import annotations

import csv as _csv
import hashlib
import io
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any
from xml.dom import minidom

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/trip", tags=["Wisconsin TRIP"])

ALLOWED_ROLES = {"founder", "agency_admin", "admin", "billing"}

MIN_BALANCE_CENTS = 2000
MIN_AGE_DAYS = 90
IDENTIFIER_TYPES = {"SSN", "DL", "FEIN"}
DEBT_STATUSES = {"candidate", "exported", "accepted", "rejected", "paid", "closed"}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


def _check_trip_eligible(svc: DominationService, tenant_id: uuid.UUID) -> dict[str, Any]:
    settings_list = svc.repo("trip_settings").list(tenant_id=tenant_id, limit=5)
    if not settings_list:
        raise HTTPException(status_code=403, detail="TRIP not configured. Set up TRIP settings first.")
    settings = sorted(settings_list, key=lambda x: x.get("created_at", ""), reverse=True)[0]
    d = settings.get("data") or {}
    if not d.get("is_government_entity"):
        raise HTTPException(status_code=403, detail="TRIP is available to eligible government agencies only.")
    if not d.get("trip_enrolled"):
        raise HTTPException(status_code=403, detail="TRIP enrollment not confirmed in settings.")
    return settings


# ─── Settings ─────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    records = svc.repo("trip_settings").list(tenant_id=current.tenant_id, limit=5)
    if not records:
        return {"configured": False, "is_government_entity": False, "trip_enrolled": False}
    return sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)[0]


@router.post("/settings")
async def upsert_settings(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    existing = svc.repo("trip_settings").list(tenant_id=current.tenant_id, limit=5)
    if existing:
        rec = sorted(existing, key=lambda x: x.get("created_at", ""), reverse=True)[0]
        data = dict(rec.get("data") or {})
        for k in ("is_government_entity", "trip_enrolled", "submission_method", "sftp_secret_ref", "notes"):
            if k in payload:
                data[k] = payload[k]
        updated = await svc.update(
            table="trip_settings",
            tenant_id=current.tenant_id,
            record_id=uuid.UUID(str(rec["id"])),
            actor_user_id=current.user_id,
            patch=data,
            expected_version=rec.get("version", 1),
            correlation_id=correlation_id,
        )
        return updated
    return await svc.create(
        table="trip_settings",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "is_government_entity": payload.get("is_government_entity", False),
            "trip_enrolled": payload.get("trip_enrolled", False),
            "submission_method": payload.get("submission_method", "file_upload"),
            "sftp_secret_ref": payload.get("sftp_secret_ref"),
            "notes": payload.get("notes"),
            "min_balance_cents": payload.get("min_balance_cents", MIN_BALANCE_CENTS),
            "min_age_days": payload.get("min_age_days", MIN_AGE_DAYS),
        },
        correlation_id=correlation_id,
    )


# ─── Debts ────────────────────────────────────────────────────────────────────

@router.get("/debts")
async def list_debts(
    status: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    _check_trip_eligible(svc, current.tenant_id)
    debts = svc.repo("trip_debts").list(tenant_id=current.tenant_id, limit=500)
    if status:
        debts = [d for d in debts if (d.get("data") or {}).get("status") == status]
    return debts


@router.post("/debts/build-candidates")
async def build_candidates(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    settings_rec = _check_trip_eligible(svc, current.tenant_id)
    settings_data = settings_rec.get("data") or {}
    min_balance = settings_data.get("min_balance_cents", MIN_BALANCE_CENTS)
    correlation_id = getattr(request.state, "correlation_id", None)
    accounts = svc.repo("ar_accounts").list(tenant_id=current.tenant_id, limit=500)
    existing_debts = svc.repo("trip_debts").list(tenant_id=current.tenant_id, limit=1000)
    existing_account_ids = {(d.get("data") or {}).get("ar_account_id") for d in existing_debts
                            if (d.get("data") or {}).get("status") not in ("paid", "closed")}
    created = []
    for acc in accounts:
        d = acc.get("data") or {}
        if d.get("status") in ("dispute", "closed"):
            continue
        if d.get("balance_cents", 0) < min_balance:
            continue
        if str(acc["id"]) in existing_account_ids:
            continue
        patient = d.get("patient_ref") or {}
        debt = await svc.create(
            table="trip_debts",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "ar_account_id": str(acc["id"]),
                "debtor_name": patient.get("name", ""),
                "identifier_type": patient.get("identifier_type", ""),
                "identifier_value_encrypted": patient.get("identifier_value_encrypted", ""),
                "balance_cents": d.get("balance_cents", 0),
                "status": "candidate",
                "last_error_code": None,
            },
            correlation_id=correlation_id,
        )
        created.append(str(debt["id"]))
    return {"created": len(created), "debt_ids": created}


@router.patch("/debts/{debt_id}")
async def update_debt(
    debt_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    debt = svc.repo("trip_debts").get(tenant_id=current.tenant_id, record_id=debt_id)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    data = dict(debt.get("data") or {})
    for field in ("debtor_name", "identifier_type", "identifier_value_encrypted", "balance_cents", "status", "last_error_code"):
        if field in payload:
            data[field] = payload[field]
    updated = await svc.update(
        table="trip_debts",
        tenant_id=current.tenant_id,
        record_id=debt_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=debt.get("version", 1),
        correlation_id=correlation_id,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Version conflict, please retry")
    return updated


# ─── Export ───────────────────────────────────────────────────────────────────

def _build_trip_xml(debts: list[dict], tenant_id: str) -> bytes:
    root = ET.Element("TRIPSubmission")
    root.set("xmlns", "http://dor.wisconsin.gov/trip/v1")
    root.set("SubmissionDate", datetime.now(UTC).strftime("%Y-%m-%d"))
    root.set("AgencyID", tenant_id)
    debts_el = ET.SubElement(root, "Debts")
    for debt in debts:
        d = debt.get("data") or {}
        debt_el = ET.SubElement(debts_el, "Debt")
        ET.SubElement(debt_el, "DebtorName").text = d.get("debtor_name", "")
        ET.SubElement(debt_el, "IdentifierType").text = d.get("identifier_type", "")
        ET.SubElement(debt_el, "IdentifierValue").text = d.get("identifier_value_encrypted", "")
        ET.SubElement(debt_el, "Balance").text = "{:.2f}".format((d.get("balance_cents") or 0) / 100)
        ET.SubElement(debt_el, "AgencyDebtID").text = str(debt["id"])
        ET.SubElement(debt_el, "ARAccountID").text = d.get("ar_account_id", "")
    raw = ET.tostring(root, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ").encode("utf-8")


@router.post("/exports/generate")
async def generate_export(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    _check_trip_eligible(svc, current.tenant_id)
    correlation_id = getattr(request.state, "correlation_id", None)
    debts = svc.repo("trip_debts").list(tenant_id=current.tenant_id, limit=500)
    exportable = [
        d for d in debts
        if (d.get("data") or {}).get("status") == "candidate"
        and (d.get("data") or {}).get("debtor_name")
        and (d.get("data") or {}).get("identifier_type") in IDENTIFIER_TYPES
        and (d.get("data") or {}).get("identifier_value_encrypted")
        and (d.get("data") or {}).get("balance_cents", 0) >= MIN_BALANCE_CENTS
    ]
    if not exportable:
        raise HTTPException(status_code=422, detail="No exportable debt candidates. Build candidates first and ensure all required fields are present.")
    xml_bytes = _build_trip_xml(exportable, str(current.tenant_id))
    sha256 = hashlib.sha256(xml_bytes).hexdigest()
    export_id = str(uuid.uuid4())
    s3_key = f"trip/exports/{current.tenant_id}/{export_id}.xml"
    try:
        from core_app.documents.s3_storage import default_exports_bucket, put_bytes
        bucket = default_exports_bucket()
        if bucket:
            put_bytes(bucket=bucket, key=s3_key, content=xml_bytes, content_type="application/xml")
    except Exception:
        pass
    export = await svc.create(
        table="trip_exports",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "exported_at": datetime.now(UTC).isoformat(),
            "method": payload.get("method", "file_upload"),
            "s3_xml_key": s3_key,
            "record_count": len(exportable),
            "sha256": sha256,
            "status": "generated",
        },
        correlation_id=correlation_id,
    )
    for d in exportable:
        ddata = dict(d.get("data") or {})
        ddata["status"] = "exported"
        await svc.update(
            table="trip_debts",
            tenant_id=current.tenant_id,
            record_id=uuid.UUID(str(d["id"])),
            actor_user_id=current.user_id,
            patch=ddata,
            expected_version=d.get("version", 1),
            correlation_id=correlation_id,
        )
    return {"export": export, "record_count": len(exportable), "sha256": sha256, "s3_key": s3_key}


@router.get("/exports")
async def list_exports(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    _check_trip_eligible(svc, current.tenant_id)
    return svc.repo("trip_exports").list(tenant_id=current.tenant_id, limit=100)


# ─── Rejects ──────────────────────────────────────────────────────────────────

@router.post("/rejects/import")
async def import_rejects(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    _check_trip_eligible(svc, current.tenant_id)
    correlation_id = getattr(request.state, "correlation_id", None)
    body = await request.body()
    rows = []
    try:
        reader = _csv.DictReader(io.StringIO(body.decode("utf-8", errors="replace")))
        rows = list(reader)
    except Exception:
        pass
    reject_import = await svc.create(
        table="trip_reject_imports",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "parsed_json": {"rows": rows},
            "imported_at": datetime.now(UTC).isoformat(),
            "row_count": len(rows),
        },
        correlation_id=correlation_id,
    )
    fix_tasks = []
    for row in rows:
        debt_id_str = row.get("AgencyDebtID") or row.get("agency_debt_id") or row.get("debt_id")
        error_code = row.get("RejectCode") or row.get("reject_code") or "UNKNOWN"
        if debt_id_str:
            try:
                debt_id = uuid.UUID(debt_id_str)
                debt = svc.repo("trip_debts").get(tenant_id=current.tenant_id, record_id=debt_id)
                if debt:
                    ddata = dict(debt.get("data") or {})
                    ddata["status"] = "rejected"
                    ddata["last_error_code"] = error_code
                    await svc.update(
                        table="trip_debts",
                        tenant_id=current.tenant_id,
                        record_id=debt_id,
                        actor_user_id=current.user_id,
                        patch=ddata,
                        expected_version=debt.get("version", 1),
                        correlation_id=correlation_id,
                    )
                    fix_tasks.append({"debt_id": debt_id_str, "error_code": error_code})
            except Exception:
                pass
    return {"import_id": str(reject_import["id"]), "rows": len(rows), "fix_tasks": fix_tasks}


# ─── Postings ─────────────────────────────────────────────────────────────────

@router.post("/postings/import")
async def import_postings(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    _check_trip_eligible(svc, current.tenant_id)
    correlation_id = getattr(request.state, "correlation_id", None)
    body = await request.body()
    rows = []
    try:
        reader = _csv.DictReader(io.StringIO(body.decode("utf-8", errors="replace")))
        rows = list(reader)
    except Exception:
        pass
    applied = 0
    unmatched = 0
    for row in rows:
        debt_id_str = row.get("AgencyDebtID") or row.get("agency_debt_id") or row.get("debt_id")
        amount_str = row.get("AmountIntercepted") or row.get("amount") or "0"
        try:
            amount_cents = int(float(amount_str.replace(",", "").replace("$", "")) * 100)
        except Exception:
            amount_cents = 0
        if not debt_id_str or amount_cents <= 0:
            unmatched += 1
            continue
        try:
            debt_id = uuid.UUID(debt_id_str)
            debt = svc.repo("trip_debts").get(tenant_id=current.tenant_id, record_id=debt_id)
            if not debt:
                unmatched += 1
                continue
            ddata = debt.get("data") or {}
            ar_account_id_str = ddata.get("ar_account_id")
            await svc.create(
                table="ar_payments",
                tenant_id=current.tenant_id,
                actor_user_id=current.user_id,
                data={
                    "account_id": ar_account_id_str,
                    "amount_cents": amount_cents,
                    "method": "trip_intercept",
                    "processor_ref": f"trip-posting-{debt_id_str}",
                    "posted_at": datetime.now(UTC).isoformat(),
                },
                correlation_id=correlation_id,
            )
            new_balance = max(0, (ddata.get("balance_cents") or 0) - amount_cents)
            ddataup = dict(ddata)
            ddataup["balance_cents"] = new_balance
            ddataup["status"] = "paid" if new_balance == 0 else "accepted"
            await svc.update(
                table="trip_debts",
                tenant_id=current.tenant_id,
                record_id=debt_id,
                actor_user_id=current.user_id,
                patch=ddataup,
                expected_version=debt.get("version", 1),
                correlation_id=correlation_id,
            )
            if ar_account_id_str:
                try:
                    ar_id = uuid.UUID(ar_account_id_str)
                    acc = svc.repo("ar_accounts").get(tenant_id=current.tenant_id, record_id=ar_id)
                    if acc:
                        adata = dict(acc.get("data") or {})
                        adata["balance_cents"] = max(0, (adata.get("balance_cents") or 0) - amount_cents)
                        if adata["balance_cents"] == 0:
                            adata["status"] = "closed"
                        await svc.update(
                            table="ar_accounts",
                            tenant_id=current.tenant_id,
                            record_id=ar_id,
                            actor_user_id=current.user_id,
                            patch=adata,
                            expected_version=acc.get("version", 1),
                            correlation_id=correlation_id,
                        )
                except Exception:
                    pass
            applied += 1
        except Exception:
            unmatched += 1
    posting = await svc.create(
        table="trip_postings",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "parsed_json": {"rows": rows},
            "imported_at": datetime.now(UTC).isoformat(),
            "applied_count": applied,
            "unmatched_count": unmatched,
            "row_count": len(rows),
        },
        correlation_id=correlation_id,
    )
    return {"posting_id": str(posting["id"]), "applied": applied, "unmatched": unmatched}


@router.get("/reports/reconciliation")
async def reconciliation_report(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    _check_trip_eligible(svc, current.tenant_id)
    debts = svc.repo("trip_debts").list(tenant_id=current.tenant_id, limit=1000)
    postings = svc.repo("trip_postings").list(tenant_id=current.tenant_id, limit=100)
    by_status: dict[str, int] = {}
    total_balance = 0
    for d in debts:
        s = (d.get("data") or {}).get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        total_balance += (d.get("data") or {}).get("balance_cents", 0)
    total_applied = sum((p.get("data") or {}).get("applied_count", 0) for p in postings)
    return {
        "debt_count": len(debts),
        "by_status": by_status,
        "total_balance_cents": total_balance,
        "total_postings": len(postings),
        "total_applied": total_applied,
    }
