from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

DATA_DIR = Path(os.getenv("FQ_DATA_DIR", Path(__file__).resolve().parents[2] / ".data"))
FILES_DIR = DATA_DIR / "generated"

router = APIRouter(prefix="/api/v1/files", tags=["files"])

@router.get("/{filename}")
def download(filename: str):
    path = FILES_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), filename=filename)
