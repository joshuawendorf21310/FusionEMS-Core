from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.ai.service import AiService, hash_input
from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/chat")
def chat(
    payload: dict,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
):
    # Founder + admins only by default
    if user.role not in ("founder", "agency_admin", "billing"):
        raise HTTPException(status_code=403, detail="Forbidden")
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    svc = AiService()
    content, meta = svc.chat(
        system="You are FusionEMS Quantum assistant. Be concise and compliant.", user=prompt
    )
    from core_app.ai.guardrails import validate_ai_output

    try:
        validated = validate_ai_output(content, task_type=str(payload.get("task_type", "general")))
        content = validated.content
    except ValueError as guard_err:
        raise HTTPException(status_code=422, detail=f"AI guardrail: {guard_err}")
    # store ai run (best effort)
    try:
        db.execute(
            text("""INSERT INTO ai_runs (tenant_id, model, prompt_version, input_hash, tool_calls, cost, status, created_at)
                    VALUES (:tid, :model, :pv, :ih, :tc::jsonb, 0, 'complete', now())"""),
            {
                "tid": str(user.tenant_id),
                "model": meta.get("model", ""),
                "pv": "v1",
                "ih": hash_input(prompt),
                "tc": json.dumps({"usage": meta.get("usage", {})}),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
    return {"response": content, "meta": meta}
