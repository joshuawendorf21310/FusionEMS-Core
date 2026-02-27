from __future__ import annotations
import uuid
import json
import hashlib
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from core_app.database import get_db
from core_app.repositories.domination_repository import DominationRepository
import os

router = APIRouter(prefix="/api/v1/founder/compliance", tags=["founder-compliance"])

_s3 = boto3.client("s3")
_ssm = boto3.client("ssm")
_sqs = boto3.client("sqs")

BUCKET = os.environ.get("KITLINK_ARTIFACTS_BUCKET", "")
APP_NAME = os.environ.get("APP_NAME", "fusionems")
STAGE = os.environ.get("STAGE", "prod")
PACK_INGEST_QUEUE_URL = os.environ.get("KITLINK_PACK_INGEST_QUEUE_URL", "")

_PACK_S3_KEYS: dict[str, str] = {
    "pack_index_v1": "compliance/packs/pack_index_v1.json",
    "WI_TRANS_309_V1": "compliance/packs/wi_trans_309_pack_v1.json",
    "WI_TRANS_309_V2": "compliance/packs/wi_trans_309_pack_v2.json",
    "DEA_CS_PACK_V1": "compliance/packs/dea_cs_pack_v1.json",
    "CAAS_GROUND_PACK_V1": "compliance/packs/caas_ground_pack_v1.json",
    "CAMTS_HEMS_PACK_V1": "compliance/packs/camts_hems_pack_v1.json",
    "HOSPITAL_EMS_PACK_V1": "compliance/packs/hospital_ems_pack_v1.json",
}

_index_cache: dict = {}
_index_cache_ts: float = 0
_INDEX_TTL = 600


def _repo(db: Session) -> DominationRepository:
    return DominationRepository(db)


def _ssm_key(pack_id: str) -> str:
    return f"/{APP_NAME}/{STAGE}/packs/{pack_id}"


def _load_pack_index() -> dict:
    global _index_cache, _index_cache_ts
    now = time.time()
    if _index_cache and (now - _index_cache_ts) < _INDEX_TTL:
        return _index_cache
    try:
        ssm_val = _ssm.get_parameter(Name=_ssm_key("index"))["Parameter"]["Value"]
        s3_key = ssm_val.replace(f"s3://{BUCKET}/", "")
    except Exception:
        s3_key = _PACK_S3_KEYS["pack_index_v1"]
    try:
        obj = _s3.get_object(Bucket=BUCKET, Key=s3_key)
        _index_cache = json.loads(obj["Body"].read())
        _index_cache_ts = now
    except Exception:
        _index_cache = {"packs": [], "recommended_sets": []}
    return _index_cache


def _load_pack_json(pack_id: str) -> dict:
    s3_key = _PACK_S3_KEYS.get(pack_id)
    if not s3_key:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found in index")
    try:
        obj = _s3.get_object(Bucket=BUCKET, Key=s3_key)
        return json.loads(obj["Body"].read())
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot load pack from S3: {e}")


def _ingest_pack(pack_id: str, tenant_id: uuid.UUID, db: Session) -> dict:
    pack_json = _load_pack_json(pack_id)
    repo = _repo(db)
    system_tid = uuid.UUID("00000000-0000-0000-0000-000000000000")

    stored = repo.list("compliance_packs", system_tid)
    existing = next((r for r in stored if r["data"].get("pack_id") == pack_id), None)
    pack_hash = hashlib.sha256(json.dumps(pack_json, sort_keys=True).encode()).hexdigest()

    if existing:
        if existing["data"].get("pack_hash") == pack_hash:
            return {"pack_id": pack_id, "status": "already_ingested", "id": str(existing["id"])}
        repo.update("compliance_packs", system_tid, existing["id"], {
            **existing["data"],
            "pack_hash": pack_hash,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "status": "staged",
        })
        pack_row_id = str(existing["id"])
    else:
        row = repo.create("compliance_packs", system_tid, {
            "pack_id": pack_id,
            "name": pack_json.get("name", pack_id),
            "jurisdiction": pack_json.get("jurisdiction"),
            "effective_date": pack_json.get("effective_date"),
            "pack_hash": pack_hash,
            "status": "staged",
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
        pack_row_id = str(row["id"])

    repo.create("compliance_pack_versions", system_tid, {
        "pack_id": pack_id,
        "pack_hash": pack_hash,
        "pack_json": pack_json,
        "versioned_at": datetime.now(timezone.utc).isoformat(),
    })

    for rule in pack_json.get("global_rules", []):
        existing_rules = repo.list("compliance_rules", system_tid)
        er = next((r for r in existing_rules if r["data"].get("pack_id") == pack_id and r["data"].get("rule_id") == rule["rule_id"]), None)
        if not er:
            repo.create("compliance_rules", system_tid, {
                "pack_id": pack_id,
                "pack_row_id": pack_row_id,
                **rule,
            })

    for report in pack_json.get("reports", []):
        existing_reports = repo.list("compliance_reports", system_tid)
        er = next((r for r in existing_reports if r["data"].get("pack_id") == pack_id and r["data"].get("report_id") == report["report_id"]), None)
        if not er:
            repo.create("compliance_reports", system_tid, {
                "pack_id": pack_id,
                "pack_row_id": pack_row_id,
                **report,
            })

    for checklist in pack_json.get("checklists", []):
        for item in checklist.get("items", []):
            existing_templates = repo.list("compliance_check_templates", system_tid)
            et = next((r for r in existing_templates if r["data"].get("pack_id") == pack_id and r["data"].get("check_id") == item["item_id"]), None)
            if not et:
                repo.create("compliance_check_templates", system_tid, {
                    "pack_id": pack_id,
                    "checklist_id": checklist["checklist_id"],
                    "check_id": item["item_id"],
                    "label": item["label"],
                    "type": item.get("type", "attestation"),
                })

    return {"pack_id": pack_id, "status": "ingested", "id": pack_row_id}


def _get_tenant_config(tenant_id: uuid.UUID, db: Session) -> dict:
    repo = _repo(db)
    rows = repo.list("tenant_compliance_config", tenant_id)
    if not rows:
        return {"active_pack_ids": [], "active_set_id": None}
    return rows[0]["data"]


def _update_tenant_config(tenant_id: uuid.UUID, patch: dict, actor: str, db: Session) -> dict:
    repo = _repo(db)
    rows = repo.list("tenant_compliance_config", tenant_id)
    now = datetime.now(timezone.utc).isoformat()
    if rows:
        existing = rows[0]
        new_data = {**existing["data"], **patch, "updated_at": now, "updated_by": actor}
        repo.update("tenant_compliance_config", tenant_id, existing["id"], new_data)
        return new_data
    data = {**patch, "updated_at": now, "updated_by": actor, "active_pack_ids": patch.get("active_pack_ids", [])}
    repo.create("tenant_compliance_config", tenant_id, data)
    return data


def _emit_audit(action: str, tenant_id: str, actor: str, before: list, after: list, db: Session):
    repo = _repo(db)
    repo.create("compliance_packs", uuid.UUID("00000000-0000-0000-0000-000000000001"), {
        "audit_action": action,
        "tenant_id": tenant_id,
        "actor": actor,
        "before_pack_ids": before,
        "after_pack_ids": after,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/packs/index")
def get_pack_index():
    index = _load_pack_index()
    return index


@router.post("/packs/{pack_id}/ingest")
def ingest_pack(pack_id: str, db: Session = Depends(get_db)):
    result = _ingest_pack(pack_id, uuid.UUID("00000000-0000-0000-0000-000000000000"), db)
    return result


@router.post("/tenants/{tenant_id}/apply-pack-set")
def apply_pack_set(
    tenant_id: str,
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: str = Query(default="founder"),
):
    set_id = payload.get("set_id")
    if not set_id:
        raise HTTPException(status_code=400, detail="set_id required")

    index = _load_pack_index()
    sets = {s["set_id"]: s for s in index.get("recommended_sets", [])}
    if set_id not in sets:
        raise HTTPException(status_code=404, detail=f"Set '{set_id}' not found")

    pack_set = sets[set_id]
    pack_ids: list[str] = pack_set["pack_ids"]
    tid = uuid.UUID(tenant_id)

    config = _get_tenant_config(tid, db)
    before = list(config.get("active_pack_ids", []))

    ingested = []
    for pack_id in pack_ids:
        result = _ingest_pack(pack_id, tid, db)
        ingested.append(result)

    new_active = list(set(before + pack_ids))
    _update_tenant_config(tid, {
        "active_pack_ids": new_active,
        "active_set_id": set_id,
    }, actor, db)

    _emit_audit("packset.applied", tenant_id, actor, before, new_active, db)

    return {
        "set_id": set_id,
        "tenant_id": tenant_id,
        "packs_applied": pack_ids,
        "ingested": ingested,
        "active_pack_ids": new_active,
        "event": "compliance.tenant.packset.applied",
    }


@router.post("/tenants/{tenant_id}/enable-pack")
def enable_pack(
    tenant_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    actor: str = Query(default="founder"),
):
    pack_id = payload.get("pack_id")
    if not pack_id:
        raise HTTPException(status_code=400, detail="pack_id required")

    tid = uuid.UUID(tenant_id)
    ingest_result = _ingest_pack(pack_id, tid, db)

    config = _get_tenant_config(tid, db)
    before = list(config.get("active_pack_ids", []))
    new_active = list(set(before + [pack_id]))
    _update_tenant_config(tid, {"active_pack_ids": new_active}, actor, db)
    _emit_audit("pack.enabled", tenant_id, actor, before, new_active, db)

    return {
        "pack_id": pack_id,
        "tenant_id": tenant_id,
        "status": "enabled",
        "ingest": ingest_result,
        "active_pack_ids": new_active,
        "event": "compliance.tenant.pack.enabled",
    }


@router.post("/tenants/{tenant_id}/disable-pack")
def disable_pack(
    tenant_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    actor: str = Query(default="founder"),
):
    pack_id = payload.get("pack_id")
    if not pack_id:
        raise HTTPException(status_code=400, detail="pack_id required")

    tid = uuid.UUID(tenant_id)
    config = _get_tenant_config(tid, db)
    before = list(config.get("active_pack_ids", []))
    new_active = [p for p in before if p != pack_id]
    _update_tenant_config(tid, {"active_pack_ids": new_active}, actor, db)
    _emit_audit("pack.disabled", tenant_id, actor, before, new_active, db)

    return {
        "pack_id": pack_id,
        "tenant_id": tenant_id,
        "status": "disabled",
        "active_pack_ids": new_active,
        "event": "compliance.tenant.pack.disabled",
    }


@router.get("/tenants/{tenant_id}/status")
def tenant_compliance_status(tenant_id: str, db: Session = Depends(get_db)):
    tid = uuid.UUID(tenant_id)
    config = _get_tenant_config(tid, db)
    active_pack_ids: list[str] = config.get("active_pack_ids", [])

    repo = _repo(db)
    system_tid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    all_packs = repo.list("compliance_packs", system_tid)
    pack_map = {r["data"].get("pack_id"): r["data"] for r in all_packs}

    inspections = repo.list("compliance_inspections", tid)
    completed = [r for r in inspections if r["data"].get("status") == "complete"]
    last_inspection = max((r["data"].get("submitted_at", "") for r in completed), default=None)
    pass_count = sum(1 for r in completed if r["data"].get("result_status") == "pass")
    fleet_score = round(pass_count / len(completed) * 100, 1) if completed else None

    active_details = []
    for pid in active_pack_ids:
        p = pack_map.get(pid, {})
        active_details.append({
            "pack_id": pid,
            "name": p.get("name", pid),
            "jurisdiction": p.get("jurisdiction"),
            "status": p.get("status", "staged"),
        })

    return {
        "tenant_id": tenant_id,
        "active_pack_ids": active_pack_ids,
        "active_set_id": config.get("active_set_id"),
        "active_packs": active_details,
        "fleet_score": fleet_score,
        "last_inspection": last_inspection,
        "inspections_total": len(completed),
        "updated_at": config.get("updated_at"),
        "updated_by": config.get("updated_by"),
    }


@router.get("/tenants")
def list_tenant_configs(db: Session = Depends(get_db)):
    repo = _repo(db)
    system_tid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    rows = repo.list("tenant_compliance_config", system_tid)
    return [{"id": str(r["id"]), "tenant_id": str(r["tenant_id"]), "data": r["data"]} for r in rows]
