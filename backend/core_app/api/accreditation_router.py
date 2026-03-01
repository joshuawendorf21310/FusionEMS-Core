from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.accreditation import (
    AccreditationDashboard,
    AccreditationItemCreate,
    AccreditationItemUpdate,
)
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/accreditation", tags=["accreditation"])

@router.post("/items")
def create_item(payload: AccreditationItemCreate, db: Session = Depends(db_session_dependency), user: CurrentUser = Depends(get_current_user)):
    row = db.execute(
        text("""
            INSERT INTO accreditation_items
            (tenant_id, standard_ref, category, required_docs, status, score_weight)
            VALUES (:tid, :ref, :cat, :docs::jsonb, 'not_started', :w)
            RETURNING id
        """),
        {"tid": str(user.tenant_id), "ref": payload.standard_ref, "cat": payload.category, "docs": json.dumps(payload.required_docs), "w": payload.score_weight},
    ).mappings().first()
    db.commit()
    return {"id": str(row["id"])}

@router.patch("/items/{item_id}")
def update_item(item_id: str, payload: AccreditationItemUpdate, db: Session = Depends(db_session_dependency), user: CurrentUser = Depends(get_current_user)):
    # optimistic concurrency
    current = db.execute(
        text("SELECT version FROM accreditation_items WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL"),
        {"id": item_id, "tid": str(user.tenant_id)}
    ).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="Not found")
    if int(current["version"]) != payload.version:
        raise HTTPException(status_code=409, detail="Version conflict")

    updates = {}
    if payload.status is not None:
        updates["status"] = payload.status
    if payload.notes is not None:
        updates["notes"] = payload.notes
    if payload.required_docs is not None:
        updates["required_docs"] = json.dumps(payload.required_docs)
    if payload.score_weight is not None:
        updates["score_weight"] = payload.score_weight

    sets = ", ".join([f"{k} = :{k}" if k != "required_docs" else "required_docs = :required_docs::jsonb" for k in updates])
    if not sets:
        return {"ok": True}

    db.execute(
        text(f"""UPDATE accreditation_items
                SET {sets}, version = version + 1, updated_at = now()
                WHERE id=:id AND tenant_id=:tid"""),
        {**updates, "id": item_id, "tid": str(user.tenant_id)}
    )
    db.commit()
    return {"ok": True}

@router.get("/dashboard", response_model=AccreditationDashboard)
def dashboard(db: Session = Depends(db_session_dependency), user: CurrentUser = Depends(get_current_user)) -> AccreditationDashboard:
    rows = db.execute(
        text("""SELECT category, status, score_weight FROM accreditation_items
                WHERE tenant_id=:tid AND deleted_at IS NULL"""),
        {"tid": str(user.tenant_id)}
    ).mappings().all()

    total_weight = sum(int(r["score_weight"]) for r in rows) or 1
    complete_weight = sum(int(r["score_weight"]) for r in rows if r["status"] == "complete")
    score = round(100.0 * complete_weight / total_weight, 2)

    by_cat = {}
    deficiencies = []
    for r in rows:
        cat = r["category"]
        by_cat.setdefault(cat, {"total": 0, "complete": 0})
        by_cat[cat]["total"] += 1
        if r["status"] == "complete":
            by_cat[cat]["complete"] += 1
        else:
            deficiencies.append({"category": cat, "status": r["status"]})

    return AccreditationDashboard(score_percent=score, by_category=by_cat, deficiencies=deficiencies)
