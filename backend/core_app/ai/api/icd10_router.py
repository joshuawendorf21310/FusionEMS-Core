from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role

router = APIRouter(prefix="/api/v1/coding", tags=["Coding"])


from fastapi import Query

@router.get("/icd10/search")
async def search(q: str = Query(...), db: Session = Depends(db_session_dependency)):
    # global search: uses icd10_codes table; simple LIKE query
    rows = db.execute(text("SELECT code, short_description FROM icd10_codes WHERE code ILIKE :q OR short_description ILIKE :q LIMIT 50"), {"q": f"%{q}%"}).fetchall()
    return [{"code": r[0], "short_description": r[1]} for r in rows]

@router.get("/icd10/{code}")
async def get_code(code: str, db: Session = Depends(db_session_dependency)):
    row = db.execute(text("SELECT code, short_description, long_description, version_year FROM icd10_codes WHERE code = :c LIMIT 1"), {"c": code}).fetchone()
    return {"code": row[0], "short_description": row[1], "long_description": row[2], "version_year": row[3]} if row else {"error":"not_found"}

@router.post("/icd10/import", dependencies=[Depends(require_role("admin","founder"))])
async def import_codes(payload: dict[str, Any], db: Session = Depends(db_session_dependency)):
    # payload expects list under 'codes' with fields: code, short_description, long_description, version_year
    codes = payload.get("codes", [])
    for c in codes:
        db.execute(text("""INSERT INTO icd10_codes (id, code, short_description, long_description, version_year, created_at, updated_at)
                             VALUES (gen_random_uuid(), :code, :sd, :ld, :vy, now(), now())
                             ON CONFLICT (code, version_year) DO NOTHING"""), {"code": c["code"], "sd": c.get("short_description",""), "ld": c.get("long_description",""), "vy": int(c.get("version_year", 0))})
    db.commit()
    return {"imported": len(codes)}

