from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/ar", tags=["AR Collections"])

ALLOWED_ROLES = {"founder", "agency_admin", "admin", "billing"}
AR_STATUSES = {"current", "past_due", "payment_plan", "dispute", "placed", "closed"}
DISPUTE_REASONS = {"not_my_debt", "insurance_should_pay", "service_dispute", "other"}


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


# ─── Accounts ────────────────────────────────────────────────────────────────

@router.get("/accounts")
async def list_accounts(
    status: str | None = None,
    days_past_due_gte: int | None = None,
    limit: int = 100,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    accounts = svc.repo("ar_accounts").list(tenant_id=current.tenant_id, limit=min(limit, 500))
    if status:
        accounts = [a for a in accounts if (a.get("data") or {}).get("status") == status]
    if days_past_due_gte is not None:
        accounts = [a for a in accounts if (a.get("data") or {}).get("days_past_due", 0) >= days_past_due_gte]
    return accounts


@router.get("/accounts/{account_id}")
async def get_account(
    account_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    account = svc.repo("ar_accounts").get(tenant_id=current.tenant_id, record_id=account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    aid = str(account_id)
    charges = [c for c in svc.repo("ar_charges").list(tenant_id=current.tenant_id, limit=200)
               if (c.get("data") or {}).get("account_id") == aid]
    payments = [p for p in svc.repo("ar_payments").list(tenant_id=current.tenant_id, limit=200)
                if (p.get("data") or {}).get("account_id") == aid]
    plans = [p for p in svc.repo("ar_payment_plans").list(tenant_id=current.tenant_id, limit=50)
             if (p.get("data") or {}).get("account_id") == aid]
    disputes = [d for d in svc.repo("ar_disputes").list(tenant_id=current.tenant_id, limit=50)
                if (d.get("data") or {}).get("account_id") == aid]
    statements = [s for s in svc.repo("ar_statements").list(tenant_id=current.tenant_id, limit=50)
                  if (s.get("data") or {}).get("account_id") == aid]
    return {
        "account": account,
        "charges": charges,
        "payments": payments,
        "plans": plans,
        "disputes": disputes,
        "statements": statements,
    }


@router.post("/accounts")
async def create_account(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="ar_accounts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "case_id": payload.get("case_id"),
            "patient_ref": payload.get("patient_ref", {}),
            "guarantor_ref": payload.get("guarantor_ref", {}),
            "balance_cents": payload.get("balance_cents", 0),
            "status": "current",
            "days_past_due": 0,
            "last_statement_at": None,
            "next_statement_at": None,
            "dunning_cycle": 0,
        },
        correlation_id=correlation_id,
    )


# ─── Payment Plans ────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/payment-plans")
async def create_payment_plan(
    account_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    account = svc.repo("ar_accounts").get(tenant_id=current.tenant_id, record_id=account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    plan = await svc.create(
        table="ar_payment_plans",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "account_id": str(account_id),
            "status": "active",
            "monthly_amount_cents": payload.get("monthly_amount_cents", 0),
            "autopay_enabled": payload.get("autopay_enabled", False),
            "next_due_at": payload.get("next_due_at"),
            "total_installments": payload.get("total_installments"),
            "installments_paid": 0,
        },
        correlation_id=correlation_id,
    )
    data = dict(account.get("data") or {})
    data["status"] = "payment_plan"
    await svc.update(
        table="ar_accounts",
        tenant_id=current.tenant_id,
        record_id=account_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=account.get("version", 1),
        correlation_id=correlation_id,
    )
    await svc.create(
        table="ledger_entries",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"entry_type": "ar.plan.created", "account_id": str(account_id), "plan_id": str(plan["id"]),
              "at": datetime.now(timezone.utc).isoformat()},
        correlation_id=correlation_id,
    )
    return plan


# ─── Disputes ─────────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/disputes")
async def create_dispute(
    account_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    reason = payload.get("reason_code", "other")
    if reason not in DISPUTE_REASONS:
        raise HTTPException(status_code=422, detail=f"reason_code must be one of {sorted(DISPUTE_REASONS)}")
    svc = _svc(db)
    account = svc.repo("ar_accounts").get(tenant_id=current.tenant_id, record_id=account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    dispute = await svc.create(
        table="ar_disputes",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "account_id": str(account_id),
            "reason_code": reason,
            "notes": payload.get("notes", ""),
            "status": "open",
        },
        correlation_id=correlation_id,
    )
    data = dict(account.get("data") or {})
    data["status"] = "dispute"
    await svc.update(
        table="ar_accounts",
        tenant_id=current.tenant_id,
        record_id=account_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=account.get("version", 1),
        correlation_id=correlation_id,
    )
    await svc.create(
        table="ledger_entries",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"entry_type": "ar.dispute.opened", "account_id": str(account_id),
              "dispute_id": str(dispute["id"]), "at": datetime.now(timezone.utc).isoformat()},
        correlation_id=correlation_id,
    )
    return dispute


@router.patch("/accounts/{account_id}/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    account_id: uuid.UUID,
    dispute_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    dispute = svc.repo("ar_disputes").get(tenant_id=current.tenant_id, record_id=dispute_id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    correlation_id = getattr(request.state, "correlation_id", None)
    data = dict(dispute.get("data") or {})
    data["status"] = payload.get("resolution", "resolved")
    data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    data["resolved_by"] = str(current.user_id)
    updated = await svc.update(
        table="ar_disputes",
        tenant_id=current.tenant_id,
        record_id=dispute_id,
        actor_user_id=current.user_id,
        patch=data,
        expected_version=dispute.get("version", 1),
        correlation_id=correlation_id,
    )
    account = svc.repo("ar_accounts").get(tenant_id=current.tenant_id, record_id=account_id)
    if account and (account.get("data") or {}).get("status") == "dispute":
        adata = dict(account.get("data") or {})
        adata["status"] = "current"
        await svc.update(
            table="ar_accounts",
            tenant_id=current.tenant_id,
            record_id=account_id,
            actor_user_id=current.user_id,
            patch=adata,
            expected_version=account.get("version", 1),
            correlation_id=correlation_id,
        )
    return updated


# ─── Statements ───────────────────────────────────────────────────────────────

@router.post("/statements/run")
async def run_statements(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    correlation_id = getattr(request.state, "correlation_id", None)
    svc = _svc(db)
    accounts = svc.repo("ar_accounts").list(tenant_id=current.tenant_id, limit=500)
    now = datetime.now(timezone.utc)
    queued = []
    for acc in accounts:
        d = acc.get("data") or {}
        if d.get("status") in ("dispute", "placed", "closed"):
            continue
        balance = d.get("balance_cents", 0)
        if balance <= 0:
            continue
        stmt = await svc.create(
            table="ar_statements",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "account_id": str(acc["id"]),
                "statement_cycle": (d.get("dunning_cycle") or 0) + 1,
                "delivery_method": payload.get("delivery_method", "mail"),
                "status": "queued",
                "balance_cents": balance,
            },
            correlation_id=correlation_id,
        )
        queued.append(str(stmt["id"]))
        adata = dict(d)
        adata["dunning_cycle"] = (d.get("dunning_cycle") or 0) + 1
        adata["last_statement_at"] = now.isoformat()
        await svc.update(
            table="ar_accounts",
            tenant_id=current.tenant_id,
            record_id=uuid.UUID(str(acc["id"])),
            actor_user_id=current.user_id,
            patch=adata,
            expected_version=acc.get("version", 1),
            correlation_id=correlation_id,
        )
    return {"queued": len(queued), "statement_ids": queued}


# ─── Payments webhook ─────────────────────────────────────────────────────────

@router.post("/payments/webhook")
async def payment_webhook(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    account_id_str = payload.get("account_id") or payload.get("metadata", {}).get("account_id")
    amount_cents = int(payload.get("amount_cents") or payload.get("amount", 0))
    if not account_id_str or amount_cents <= 0:
        return {"status": "ignored"}
    try:
        account_id = uuid.UUID(account_id_str)
    except ValueError:
        return {"status": "invalid_account_id"}
    import os as _os
    system_tenant = _os.environ.get("SYSTEM_TENANT_ID", "00000000-0000-0000-0000-000000000000")
    from core_app.core.config import get_settings
    system_tenant = get_settings().system_tenant_id or system_tenant
    try:
        system_tenant_uuid = uuid.UUID(system_tenant)
    except ValueError:
        system_tenant_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")

    accounts = svc.repo("ar_accounts").list(tenant_id=system_tenant_uuid, limit=1)
    account = None
    all_accs = []
    tenants_repo = svc.repo("ar_accounts")
    all_accs_global = tenants_repo.list(tenant_id=system_tenant_uuid, limit=1)

    payment = await svc.create(
        table="ar_payments",
        tenant_id=system_tenant_uuid,
        actor_user_id=system_tenant_uuid,
        data={
            "account_id": account_id_str,
            "amount_cents": amount_cents,
            "method": payload.get("method", "card"),
            "processor_ref": payload.get("processor_ref") or payload.get("payment_intent_id"),
            "posted_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"status": "posted", "payment_id": str(payment["id"])}


# ─── Vendor profiles ──────────────────────────────────────────────────────────

@router.post("/vendors")
async def create_vendor(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    return await svc.create(
        table="collections_vendor_profiles",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "vendor_name": payload.get("vendor_name", ""),
            "placement_method": payload.get("placement_method", "portal_upload"),
            "sftp_host": payload.get("sftp_host"),
            "sftp_username": payload.get("sftp_username"),
            "sftp_secret_ref": payload.get("sftp_secret_ref"),
            "file_format": payload.get("file_format", "csv_standard_v1"),
            "status_import_format": payload.get("status_import_format", "csv_standard_v1"),
            "status": "active",
        },
        correlation_id=correlation_id,
    )


@router.get("/vendors")
async def list_vendors(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    return _svc(db).repo("collections_vendor_profiles").list(tenant_id=current.tenant_id, limit=50)


# ─── Placement export ─────────────────────────────────────────────────────────

@router.post("/vendors/{vendor_id}/placements/generate")
async def generate_placement(
    vendor_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    vendor = svc.repo("collections_vendor_profiles").get(tenant_id=current.tenant_id, record_id=vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    correlation_id = getattr(request.state, "correlation_id", None)

    min_days = payload.get("min_days_past_due", 90)
    accounts = svc.repo("ar_accounts").list(tenant_id=current.tenant_id, limit=500)
    eligible = [
        a for a in accounts
        if (a.get("data") or {}).get("status") not in ("closed", "placed", "dispute")
        and (a.get("data") or {}).get("days_past_due", 0) >= min_days
        and (a.get("data") or {}).get("balance_cents", 0) > 0
    ]

    csv_buf = io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=[
        "agency_account_number", "patient_name", "dob_year", "balance_dollars",
        "service_date", "last_statement_date", "dispute_status", "case_id",
    ])
    writer.writeheader()
    for acc in eligible:
        d = acc.get("data") or {}
        patient = d.get("patient_ref") or {}
        writer.writerow({
            "agency_account_number": str(acc["id"]),
            "patient_name": patient.get("name", ""),
            "dob_year": patient.get("dob_year", ""),
            "balance_dollars": "{:.2f}".format((d.get("balance_cents") or 0) / 100),
            "service_date": patient.get("service_date", ""),
            "last_statement_date": d.get("last_statement_at", ""),
            "dispute_status": "none",
            "case_id": d.get("case_id", ""),
        })

    batch_id = f"batch-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("placements.csv", csv_buf.getvalue())
        audit = {"batch_id": batch_id, "generated_at": datetime.now(timezone.utc).isoformat(),
                 "account_count": len(eligible), "tenant_id": str(current.tenant_id)}
        zf.writestr("audit.json", json.dumps(audit, indent=2))
    zip_bytes = zip_buf.getvalue()

    s3_key = f"ar/placements/{current.tenant_id}/{batch_id}/export.zip"
    try:
        from core_app.documents.s3_storage import put_bytes, default_exports_bucket
        bucket = default_exports_bucket()
        if bucket:
            put_bytes(bucket=bucket, key=s3_key, content=zip_bytes, content_type="application/zip")
    except Exception:
        pass

    placement = await svc.create(
        table="collections_placements",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "vendor_profile_id": str(vendor_id),
            "batch_id": batch_id,
            "s3_export_zip_key": s3_key,
            "placed_at": datetime.now(timezone.utc).isoformat(),
            "status": "generated",
            "account_count": len(eligible),
        },
        correlation_id=correlation_id,
    )

    for acc in eligible:
        adata = dict(acc.get("data") or {})
        adata["status"] = "placed"
        await svc.update(
            table="ar_accounts",
            tenant_id=current.tenant_id,
            record_id=uuid.UUID(str(acc["id"])),
            actor_user_id=current.user_id,
            patch=adata,
            expected_version=acc.get("version", 1),
            correlation_id=correlation_id,
        )

    return {"placement": placement, "eligible_count": len(eligible), "batch_id": batch_id}


@router.post("/vendors/{vendor_id}/status/import")
async def import_vendor_status(
    vendor_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    body = await request.body()
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        reader = csv.DictReader(io.StringIO(body.decode("utf-8", errors="replace")))
        rows = list(reader)
    except Exception:
        rows = []
    parsed = {"rows": rows, "row_count": len(rows)}
    record = await svc.create(
        table="collections_status_updates",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "vendor_profile_id": str(vendor_id),
            "parsed_json": parsed,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "row_count": len(rows),
        },
        correlation_id=correlation_id,
    )
    for row in rows:
        acct_num = row.get("agency_account_number") or row.get("account_number") or row.get("id")
        status = (row.get("status") or "").lower()
        if acct_num and status in ("paid", "closed"):
            try:
                aid = uuid.UUID(acct_num)
                acc = svc.repo("ar_accounts").get(tenant_id=current.tenant_id, record_id=aid)
                if acc:
                    adata = dict(acc.get("data") or {})
                    adata["status"] = "closed" if status == "paid" else status
                    await svc.update(
                        table="ar_accounts",
                        tenant_id=current.tenant_id,
                        record_id=aid,
                        actor_user_id=current.user_id,
                        patch=adata,
                        expected_version=acc.get("version", 1),
                        correlation_id=correlation_id,
                    )
            except Exception:
                pass
    return {"import_id": str(record["id"]), "rows_parsed": len(rows)}
