from __future__ import annotations

import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core_app.api.dependencies import get_current_user_optional
from core_app.services.founder_service import (
    get_founder_status,
    save_founder_settings,
    create_document_for_founder,
)

router = APIRouter(prefix="/api/v1/founder", tags=["founder"])

class Keys(BaseModel):
    openai_api_key: str | None = None
    telnyx_api_key: str | None = None
    telnyx_public_key: str | None = None
    stripe_secret_key: str | None = None
    lob_api_key: str | None = None
    ses_from_email: str | None = None

class SaveSettingsRequest(BaseModel):
    founder_email: str = Field(..., min_length=3)
    keys: Keys

class CreateDocRequest(BaseModel):
    kind: str = Field(..., pattern="^(word|excel|invoice)$")
    title: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., max_length=20000)

@router.get("/status")
def status(user=Depends(get_current_user_optional)):
    return get_founder_status()

@router.post("/settings")
def settings(req: SaveSettingsRequest, user=Depends(get_current_user_optional)):
    # Founder is single-operator; endpoint is protected in production via RBAC.
    save_founder_settings(req.founder_email, req.keys.model_dump())
    return {"ok": True}

@router.post("/documents")
def documents(req: CreateDocRequest, user=Depends(get_current_user_optional)):
    return create_document_for_founder(req.kind, req.title, req.body)
