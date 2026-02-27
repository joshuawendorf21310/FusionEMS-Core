from __future__ import annotations
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core_app.database import get_db
from core_app.repositories.domination_repository import DominationRepository

router = APIRouter(prefix="/api/v1/kitlink", tags=["kitlink"])

_STARTER_TEMPLATES: dict[str, dict] = {
    "NARC_BOX_V1": {
        "name": "Narc Box (Controlled Substances)",
        "kit_type": "narcotics",
        "requires_seal": True,
        "requires_count": True,
        "requires_witness_waste": True,
        "compartments": [
            {
                "label": "Schedule II",
                "items": [
                    {"name": "Morphine Sulfate 10mg/mL", "controlled_schedule": "II", "unit": "vial", "par_qty": 4},
                    {"name": "Fentanyl 100mcg/2mL", "controlled_schedule": "II", "unit": "vial", "par_qty": 4},
                    {"name": "Ketamine 500mg/10mL", "controlled_schedule": "II", "unit": "vial", "par_qty": 2},
                ],
            },
            {
                "label": "Schedule III–V",
                "items": [
                    {"name": "Midazolam 5mg/mL", "controlled_schedule": "III", "unit": "vial", "par_qty": 4},
                    {"name": "Diazepam 5mg/mL", "controlled_schedule": "IV", "unit": "vial", "par_qty": 2},
                    {"name": "Lorazepam 2mg/mL", "controlled_schedule": "IV", "unit": "vial", "par_qty": 2},
                ],
            },
            {
                "label": "Naloxone / Rescue",
                "items": [
                    {"name": "Naloxone 2mg/2mL", "controlled_schedule": None, "unit": "vial", "par_qty": 6},
                    {"name": "Naloxone Intranasal 4mg", "controlled_schedule": None, "unit": "device", "par_qty": 2},
                ],
            },
            {
                "label": "Supplies",
                "items": [
                    {"name": "Waste Bag (biohazard)", "controlled_schedule": None, "unit": "each", "par_qty": 10},
                    {"name": "Witness Form", "controlled_schedule": None, "unit": "form", "par_qty": 5},
                ],
            },
            {
                "label": "Seals",
                "items": [
                    {"name": "Numbered Security Seal", "controlled_schedule": None, "unit": "each", "par_qty": 20},
                ],
            },
        ],
    },
    "AIRWAY_KIT_V1": {
        "name": "Airway Kit",
        "kit_type": "airway",
        "requires_seal": False,
        "requires_count": False,
        "requires_witness_waste": False,
        "compartments": [
            {
                "label": "BVM & Oxygen",
                "items": [
                    {"name": "BVM Adult", "unit": "each", "par_qty": 1},
                    {"name": "BVM Pediatric", "unit": "each", "par_qty": 1},
                    {"name": "NRB Mask Adult", "unit": "each", "par_qty": 2},
                    {"name": "Nasal Cannula", "unit": "each", "par_qty": 2},
                ],
            },
            {
                "label": "Supraglottic Airways",
                "items": [
                    {"name": "King LT Size 3", "unit": "each", "par_qty": 1},
                    {"name": "King LT Size 4", "unit": "each", "par_qty": 1},
                    {"name": "King LT Size 5", "unit": "each", "par_qty": 1},
                    {"name": "iGel Size 3", "unit": "each", "par_qty": 1},
                    {"name": "iGel Size 4", "unit": "each", "par_qty": 1},
                ],
            },
            {
                "label": "Intubation",
                "items": [
                    {"name": "ETT 7.0", "unit": "each", "par_qty": 2},
                    {"name": "ETT 7.5", "unit": "each", "par_qty": 2},
                    {"name": "ETT 8.0", "unit": "each", "par_qty": 2},
                    {"name": "Laryngoscope Handle", "unit": "each", "par_qty": 1},
                    {"name": "Mac 3 Blade", "unit": "each", "par_qty": 1},
                    {"name": "Mac 4 Blade", "unit": "each", "par_qty": 1},
                    {"name": "Stylet Adult", "unit": "each", "par_qty": 2},
                    {"name": "ETCO2 Colorimetric", "unit": "each", "par_qty": 2},
                ],
            },
            {
                "label": "Surgical Airway",
                "items": [
                    {"name": "Cric Kit", "unit": "each", "par_qty": 1},
                ],
            },
        ],
    },
    "TRAUMA_KIT_V1": {
        "name": "Trauma Kit",
        "kit_type": "trauma",
        "requires_seal": True,
        "requires_count": False,
        "requires_witness_waste": False,
        "compartments": [
            {
                "label": "Hemorrhage Control",
                "items": [
                    {"name": "CAT Tourniquet", "unit": "each", "par_qty": 4},
                    {"name": "Combat Gauze XL", "unit": "each", "par_qty": 4},
                    {"name": "Israeli Bandage 6-inch", "unit": "each", "par_qty": 4},
                    {"name": "Chest Seal (vented pair)", "unit": "pair", "par_qty": 2},
                    {"name": "Needle Decompression 14g 3.25in", "unit": "each", "par_qty": 2},
                ],
            },
            {
                "label": "Burns / Dressings",
                "items": [
                    {"name": "4x4 Gauze", "unit": "each", "par_qty": 20},
                    {"name": "ABD Pad 5x9", "unit": "each", "par_qty": 6},
                    {"name": "Burn Sheet", "unit": "each", "par_qty": 1},
                    {"name": "Ace Bandage 4-inch", "unit": "each", "par_qty": 4},
                ],
            },
            {
                "label": "Splinting / Immobilization",
                "items": [
                    {"name": "SAM Splint 36-inch", "unit": "each", "par_qty": 2},
                    {"name": "Traction Splint", "unit": "each", "par_qty": 1},
                    {"name": "Cervical Collar Adult (adjustable)", "unit": "each", "par_qty": 2},
                ],
            },
        ],
    },
    "IV_KIT_V1": {
        "name": "IV / Fluid Kit",
        "kit_type": "iv_fluids",
        "requires_seal": False,
        "requires_count": False,
        "requires_witness_waste": False,
        "compartments": [
            {
                "label": "IV Access",
                "items": [
                    {"name": "14g IV Catheter", "unit": "each", "par_qty": 4},
                    {"name": "16g IV Catheter", "unit": "each", "par_qty": 4},
                    {"name": "18g IV Catheter", "unit": "each", "par_qty": 6},
                    {"name": "20g IV Catheter", "unit": "each", "par_qty": 4},
                    {"name": "IO Drill + Needle Adult", "unit": "each", "par_qty": 1},
                    {"name": "Tegaderm Dressing", "unit": "each", "par_qty": 10},
                ],
            },
            {
                "label": "IV Fluids",
                "items": [
                    {"name": "Normal Saline 1000mL", "unit": "bag", "par_qty": 4, "is_fluid": True},
                    {"name": "LR 1000mL", "unit": "bag", "par_qty": 2, "is_fluid": True},
                    {"name": "Normal Saline 500mL", "unit": "bag", "par_qty": 2, "is_fluid": True},
                    {"name": "D50W 50mL", "unit": "vial", "par_qty": 2},
                ],
            },
            {
                "label": "Tubing & Administration",
                "items": [
                    {"name": "Macro Drip Tubing", "unit": "each", "par_qty": 4},
                    {"name": "Micro Drip Tubing", "unit": "each", "par_qty": 2},
                    {"name": "Blood Tubing", "unit": "each", "par_qty": 2},
                    {"name": "Extension Set", "unit": "each", "par_qty": 4},
                    {"name": "Needleless Connector", "unit": "each", "par_qty": 10},
                ],
            },
        ],
    },
}


def _repo(db: Session = Depends(get_db)) -> DominationRepository:
    return DominationRepository(db)


def _tid(tenant_id: str | None = Query(None)) -> uuid.UUID:
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")
    return uuid.UUID(tenant_id)


# ---------------------------------------------------------------------------
# Inventory Items
# ---------------------------------------------------------------------------

@router.post("/items")
def create_item(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    item = repo.create("inventory_items", tid, payload)
    return {"id": str(item["id"]), "data": item["data"]}


@router.get("/items")
def list_items(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("inventory_items", tid)
    return [{"id": str(r["id"]), "data": r["data"]} for r in rows]


# ---------------------------------------------------------------------------
# Formulary
# ---------------------------------------------------------------------------

@router.post("/formulary")
def create_formulary(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.create("formulary_items", tid, payload)
    return {"id": str(row["id"]), "data": row["data"]}


@router.get("/formulary")
def list_formulary(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("formulary_items", tid)
    return [{"id": str(r["id"]), "data": r["data"]} for r in rows]


# ---------------------------------------------------------------------------
# Kit Templates
# ---------------------------------------------------------------------------

@router.post("/kits")
def create_kit(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.create("kit_templates", tid, payload)
    return {"id": str(row["id"]), "data": row["data"]}


@router.get("/kits")
def list_kits(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("kit_templates", tid)
    return [{"id": str(r["id"]), "data": r["data"]} for r in rows]


@router.post("/kits/{kit_id}/compartments")
def add_compartment(kit_id: str, payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    payload["kit_template_id"] = kit_id
    row = repo.create("kit_compartments", tid, payload)
    return {"id": str(row["id"]), "data": row["data"]}


@router.post("/kits/starter/{key}/clone")
def clone_starter_kit(key: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    if key not in _STARTER_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Starter template '{key}' not found")
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    tmpl = _STARTER_TEMPLATES[key]
    compartments = tmpl.pop("compartments", [])
    kit_row = repo.create("kit_templates", tid, {**tmpl, "source_key": key})
    kit_id = str(kit_row["id"])
    comp_ids = []
    for comp in compartments:
        items = comp.pop("items", [])
        comp_row = repo.create("kit_compartments", tid, {**comp, "kit_template_id": kit_id})
        comp_id = str(comp_row["id"])
        for item in items:
            repo.create("compartment_items", tid, {**item, "compartment_id": comp_id, "kit_template_id": kit_id})
        comp_ids.append(comp_id)
    return {"kit_id": kit_id, "compartment_count": len(comp_ids), "source_key": key}


# ---------------------------------------------------------------------------
# Unit Layouts
# ---------------------------------------------------------------------------

@router.post("/layouts")
def create_layout(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.create("unit_layouts", tid, {**payload, "status": "draft"})
    return {"id": str(row["id"]), "data": row["data"]}


@router.get("/layouts")
def list_layouts(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("unit_layouts", tid)
    return [{"id": str(r["id"]), "data": r["data"]} for r in rows]


@router.post("/layouts/{layout_id}/publish")
def publish_layout(layout_id: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.update("unit_layouts", tid, uuid.UUID(layout_id), {"status": "active", "published_at": datetime.now(timezone.utc).isoformat()})
    if not row:
        raise HTTPException(status_code=404, detail="Layout not found")
    return {"id": layout_id, "status": "active"}


# ---------------------------------------------------------------------------
# AR Markers
# ---------------------------------------------------------------------------

@router.post("/ar/markers/generate")
def generate_marker(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    marker_code = f"KL-{str(uuid.uuid4())[:8].upper()}"
    row = repo.create("ar_markers", tid, {
        **payload,
        "marker_code": marker_code,
        "status": "pending_print",
        "format": payload.get("format", "qr"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": str(row["id"]), "marker_code": marker_code, "status": "pending_print"}


@router.get("/ar/markers/sheet.pdf")
def get_marker_sheet(sheet_id: str = Query(...), db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("ar_marker_sheets", tid)
    sheet = next((r for r in rows if str(r["id"]) == sheet_id), None)
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")
    s3_key = sheet["data"].get("s3_key")
    return {"sheet_id": sheet_id, "s3_key": s3_key, "download_url": f"https://s3.amazonaws.com/{s3_key}"}


@router.post("/ar/markers/{marker_id}/mark-printed")
def mark_printed(marker_id: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.update("ar_markers", tid, uuid.UUID(marker_id), {"status": "printed", "printed_at": datetime.now(timezone.utc).isoformat()})
    if not row:
        raise HTTPException(status_code=404, detail="Marker not found")
    return {"id": marker_id, "status": "printed"}


@router.post("/ar/markers/{marker_id}/activate")
def activate_marker(marker_id: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.update("ar_markers", tid, uuid.UUID(marker_id), {"status": "active", "activated_at": datetime.now(timezone.utc).isoformat()})
    if not row:
        raise HTTPException(status_code=404, detail="Marker not found")
    return {"id": marker_id, "status": "active"}


@router.get("/ar/resolve/{marker_code}")
def resolve_marker(marker_code: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("ar_markers", tid)
    marker = next((r for r in rows if r["data"].get("marker_code") == marker_code), None)
    if not marker:
        raise HTTPException(status_code=404, detail="Marker not found")
    entity_type = marker["data"].get("entity_type", "kit")
    entity_id = marker["data"].get("entity_id")
    next_steps = []
    if entity_type == "kit":
        next_steps = ["verify_seal", "count_narcotics", "check_expiry"]
    elif entity_type == "unit":
        next_steps = ["shift_start_check", "verify_layout"]
    elif entity_type == "stock_location":
        next_steps = ["view_stock_balances", "create_transaction"]
    return {
        "marker_code": marker_code,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "status": marker["data"].get("status"),
        "next_steps": next_steps,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Shift Checks
# ---------------------------------------------------------------------------

@router.post("/checks/shift-start")
def shift_start_check(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    seal_code = payload.get("seal_code")
    narc_counts = payload.get("narc_counts", [])
    unit_id = payload.get("unit_id")
    crew_user_id = payload.get("crew_user_id")

    discrepancies = []
    for count_entry in narc_counts:
        expected = count_entry.get("expected_qty", 0)
        actual = count_entry.get("actual_qty", 0)
        if expected != actual:
            disc = repo.create("narc_discrepancies", tid, {
                "item_name": count_entry.get("item_name"),
                "expected_qty": expected,
                "actual_qty": actual,
                "delta": actual - expected,
                "unit_id": unit_id,
                "crew_user_id": crew_user_id,
                "shift_type": "start",
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            discrepancies.append({"id": str(disc["id"]), "item": count_entry.get("item_name"), "delta": actual - expected})

    count_row = repo.create("narc_counts", tid, {
        "unit_id": unit_id,
        "crew_user_id": crew_user_id,
        "seal_code": seal_code,
        "shift_type": "start",
        "counts": narc_counts,
        "discrepancy_count": len(discrepancies),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    blocked = len(discrepancies) > 0
    return {
        "count_id": str(count_row["id"]),
        "discrepancies": discrepancies,
        "blocked": blocked,
        "message": "Discrepancy found — supervisor alert required" if blocked else "Shift start check complete",
    }


@router.post("/checks/shift-end")
def shift_end_check(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    count_row = repo.create("narc_counts", tid, {
        **payload,
        "shift_type": "end",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"count_id": str(count_row["id"]), "status": "complete"}


# ---------------------------------------------------------------------------
# Restock
# ---------------------------------------------------------------------------

@router.post("/restock/submit")
def submit_restock(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    lines = payload.pop("lines", [])
    txn = repo.create("inventory_transactions", tid, {
        **payload,
        "txn_type": "restock",
        "status": "posted",
        "posted_at": datetime.now(timezone.utc).isoformat(),
    })
    txn_id = str(txn["id"])
    line_ids = []
    for line in lines:
        lr = repo.create("inventory_transaction_lines", tid, {**line, "transaction_id": txn_id})
        line_ids.append(str(lr["id"]))
    return {"transaction_id": txn_id, "line_count": len(line_ids), "status": "posted"}


# ---------------------------------------------------------------------------
# Narcotics
# ---------------------------------------------------------------------------

@router.post("/narc/seal/scan")
def narc_seal_scan(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    row = repo.create("narc_seals", tid, {
        **payload,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "status": "verified",
    })
    return {"id": str(row["id"]), "status": "verified"}


@router.post("/narc/count")
def narc_count(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    counts = payload.get("counts", [])
    discrepancies = []
    for c in counts:
        if c.get("expected_qty", 0) != c.get("actual_qty", 0):
            dr = repo.create("narc_discrepancies", tid, {
                "item_name": c.get("item_name"),
                "expected_qty": c.get("expected_qty"),
                "actual_qty": c.get("actual_qty"),
                "delta": c.get("actual_qty", 0) - c.get("expected_qty", 0),
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            discrepancies.append({"id": str(dr["id"]), "item": c.get("item_name")})
    row = repo.create("narc_counts", tid, {
        **payload,
        "discrepancy_count": len(discrepancies),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"count_id": str(row["id"]), "discrepancies": discrepancies}


@router.post("/narc/waste")
def narc_waste(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    if not payload.get("witness_user_id"):
        raise HTTPException(status_code=400, detail="witness_user_id is required for waste events")
    row = repo.create("narc_waste_events", tid, {
        **payload,
        "wasted_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": str(row["id"]), "status": "recorded"}


# ---------------------------------------------------------------------------
# Transactions (manual)
# ---------------------------------------------------------------------------

@router.post("/transactions")
def manual_transaction(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    lines = payload.pop("lines", [])
    txn = repo.create("inventory_transactions", tid, {
        **payload,
        "status": "posted",
        "posted_at": datetime.now(timezone.utc).isoformat(),
    })
    txn_id = str(txn["id"])
    for line in lines:
        repo.create("inventory_transaction_lines", tid, {**line, "transaction_id": txn_id})
    return {"transaction_id": txn_id, "line_count": len(lines)}


# ---------------------------------------------------------------------------
# ePCR Usage Hook
# ---------------------------------------------------------------------------

@router.post("/epcr-usage-hook")
def epcr_usage_hook(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    usages = payload.get("usages", [])
    txn = repo.create("inventory_transactions", tid, {
        "txn_type": "epcr_deduct",
        "incident_id": payload.get("incident_id"),
        "epcr_id": payload.get("epcr_id"),
        "unit_id": payload.get("unit_id"),
        "status": "posted",
        "posted_at": datetime.now(timezone.utc).isoformat(),
    })
    txn_id = str(txn["id"])
    for usage in usages:
        repo.create("inventory_transaction_lines", tid, {
            **usage,
            "transaction_id": txn_id,
            "direction": "out",
        })
    return {"transaction_id": txn_id, "deducted_count": len(usages)}


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

@router.post("/ocr/scan")
def ocr_scan(payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    job_id = str(uuid.uuid4())
    s3_key = f"kitlink/scans/{tid}/{job_id}.jpg"
    row = repo.create("kitlink_ocr_jobs", tid, {
        "job_id": job_id,
        "s3_key": s3_key,
        "status": "pending",
        "context": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    presigned_url = f"https://s3.amazonaws.com/BUCKET/{s3_key}?presigned=1"
    return {"job_id": str(row["id"]), "upload_url": presigned_url, "s3_key": s3_key}


@router.get("/ocr/jobs/{job_id}")
def get_ocr_job(job_id: str, db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("kitlink_ocr_jobs", tid)
    job = next((r for r in rows if str(r["id"]) == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="OCR job not found")
    return {"id": job_id, "data": job["data"]}


@router.post("/ocr/jobs/{job_id}/confirm")
def confirm_ocr_job(job_id: str, payload: dict[str, Any], db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("kitlink_ocr_jobs", tid)
    job = next((r for r in rows if str(r["id"]) == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="OCR job not found")
    updated = repo.update("kitlink_ocr_jobs", tid, uuid.UUID(job_id), {
        **job["data"],
        "status": "confirmed",
        "confirmed_data": payload,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": job_id, "status": "confirmed"}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@router.get("/reports/expiring")
def report_expiring(days: int = Query(30), db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("stock_balances", tid)
    cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    expiring = [
        {"id": str(r["id"]), "data": r["data"]}
        for r in rows
        if r["data"].get("expiration_date") and r["data"]["expiration_date"] <= cutoff
    ]
    return {"days": days, "expiring_count": len(expiring), "items": expiring}


@router.get("/reports/discrepancies")
def report_discrepancies(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("narc_discrepancies", tid)
    open_disc = [r for r in rows if r["data"].get("status") == "open"]
    return {"open_count": len(open_disc), "items": [{"id": str(r["id"]), "data": r["data"]} for r in open_disc]}


@router.get("/reports/par-misses")
def report_par_misses(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("stock_balances", tid)
    misses = [
        {"id": str(r["id"]), "data": r["data"]}
        for r in rows
        if (r["data"].get("current_qty", 0) < r["data"].get("par_qty", 0))
    ]
    return {"par_miss_count": len(misses), "items": misses}


@router.get("/reports/narcotics-log")
def report_narcotics_log(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    counts = repo.list("narc_counts", tid)
    waste = repo.list("narc_waste_events", tid)
    discs = repo.list("narc_discrepancies", tid)
    return {
        "counts": [{"id": str(r["id"]), "data": r["data"]} for r in counts],
        "waste_events": [{"id": str(r["id"]), "data": r["data"]} for r in waste],
        "discrepancies": [{"id": str(r["id"]), "data": r["data"]} for r in discs],
    }


@router.get("/reports/usage-by-unit")
def report_usage_by_unit(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("inventory_transaction_lines", tid)
    by_unit: dict[str, list] = {}
    for r in rows:
        unit = r["data"].get("unit_id", "unknown")
        by_unit.setdefault(unit, []).append({"id": str(r["id"]), "data": r["data"]})
    return {"by_unit": by_unit}


@router.get("/reports/usage-by-crew")
def report_usage_by_crew(db: Session = Depends(get_db), tenant_id: str = Query(...)):
    repo = _repo(db)
    tid = uuid.UUID(tenant_id)
    rows = repo.list("inventory_transaction_lines", tid)
    by_crew: dict[str, list] = {}
    for r in rows:
        crew = r["data"].get("crew_user_id", "unknown")
        by_crew.setdefault(crew, []).append({"id": str(r["id"]), "data": r["data"]})
    return {"by_crew": by_crew}
