from fastapi import APIRouter, Depends
from core_app.api.dependencies import get_current_user
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/neris", tags=["neris"])

@router.post("/exports")
def create_export(payload: dict, user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"batch_id": "TODO", "status": "queued"}

@router.get("/exports/{batch_id}")
def get_export(batch_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"batch_id": batch_id, "status": "TODO"}
