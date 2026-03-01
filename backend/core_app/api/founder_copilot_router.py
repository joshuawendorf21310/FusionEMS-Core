from __future__ import annotations

import contextlib
import json
import logging
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.ai.service import AiService
from core_app.api.dependencies import db_session_dependency, require_role
from core_app.core.config import get_settings
from core_app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/founder/copilot", tags=["Founder Copilot"])

_SYSTEM_PROMPT = """\
You are the Founder Copilot for FusionEMS Quantum — an AI assistant embedded in the Founder dashboard.
You help the founder:
  - Answer questions about the platform, tenants, billing, compliance, and infrastructure
  - Generate plans and tickets for new features or fixes
  - Produce code change proposals as structured action plans with unified diffs
  - Propose CloudFormation template modifications
  - Generate Alembic migration scripts

SAFETY RULES (non-negotiable):
  1. Never silently modify production. Every change must be proposed, shown, and approved first.
  2. Never include real secrets, API keys, or passwords in any payload.
  3. Never propose deleting audit tables, compliance logs, or migration history.
  4. Never bypass release gates (tsc, ruff, pytest, cfn-lint, alembic).
  5. Always list acceptance_tests for any CODE_CHANGE intent.

When you want to propose code changes, output your conversational reply followed by a JSON block
enclosed in ```action_plan ... ``` fences with this exact schema:

{
  "intent": "CODE_CHANGE",
  "summary": "...",
  "risk_level": "low|medium|high",
  "actions": [
    {"type": "CREATE_FILE|UPDATE_FILE|DELETE_FILE|APPLY_PATCH|GENERATE_MIGRATION|RUN_COMMAND|RUN_RELEASE_GATE|UPDATE_CLOUDFORMATION|GENERATE_REPORT|OPEN_PR", "payload": {...}}
  ],
  "acceptance_tests": ["..."],
  "notes": "..."
}

For INFO_ONLY or PLAN_ONLY intents, omit the JSON block entirely and just respond conversationally.
"""


def _db_now_sql() -> str:
    return "now()"


def _get_session_or_404(db: Session, session_id: uuid.UUID, founder_user_id: uuid.UUID) -> dict[str, Any]:
    row = db.execute(
        text("SELECT id, founder_user_id, title, created_at, updated_at FROM founder_chat_sessions WHERE id = :sid"),
        {"sid": str(session_id)},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(row["founder_user_id"]) != str(founder_user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return dict(row)


def _get_run_or_404(db: Session, run_id: uuid.UUID, founder_user_id: uuid.UUID) -> dict[str, Any]:
    row = db.execute(
        text("""
            SELECT r.id, r.session_id, r.status, r.plan_json, r.release_gate_results_json,
                   r.diff_text, r.diff_s3_key, r.gh_run_id, r.gh_run_url, r.created_at, r.updated_at,
                   s.founder_user_id
            FROM founder_chat_runs r
            JOIN founder_chat_sessions s ON s.id = r.session_id
            WHERE r.id = :rid
        """),
        {"rid": str(run_id)},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if str(row["founder_user_id"]) != str(founder_user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return dict(row)


def _parse_action_plan(assistant_text: str) -> dict[str, Any] | None:
    start = assistant_text.find("```action_plan")
    if start == -1:
        return None
    end = assistant_text.find("```", start + 14)
    if end == -1:
        return None
    raw = assistant_text[start + 14:end].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _insert_message(db: Session, session_id: uuid.UUID, role: str, content_text: str, content_json: dict | None = None) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO founder_chat_messages (session_id, role, content_text, content_json)
            VALUES (:sid, :role, :ct, :cj)
            RETURNING id, session_id, role, content_text, content_json, created_at
        """),
        {"sid": str(session_id), "role": role, "ct": content_text, "cj": json.dumps(content_json) if content_json else None},
    ).mappings().first()
    db.commit()
    return dict(row)


def _log_audit(db: Session, action: str, founder_user_id: uuid.UUID, payload: dict[str, Any]) -> None:
    with contextlib.suppress(Exception):
        db.execute(
            text("""
                INSERT INTO founder_chat_sessions (id, founder_user_id, title)
                SELECT gen_random_uuid(), :uid, :action
                WHERE false
            """),
            {"uid": str(founder_user_id), "action": action},
        )
    try:
        db.execute(
            text("""
                INSERT INTO audit_events (tenant_id, actor_user_id, action, entity_name, entity_id, field_changes)
                VALUES (:tid, :uid, :action, 'founder_copilot', gen_random_uuid(), :payload::jsonb)
                ON CONFLICT DO NOTHING
            """),
            {
                "tid": str(uuid.UUID(int=0)),
                "uid": str(founder_user_id),
                "action": action,
                "payload": json.dumps(payload),
            },
        )
        db.commit()
    except Exception as exc:
        logger.warning("audit_log_failed action=%s err=%s", action, exc)


@router.post("/sessions")
async def create_session(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    title = str(payload.get("title") or "New session")[:255]
    row = db.execute(
        text("""
            INSERT INTO founder_chat_sessions (founder_user_id, title)
            VALUES (:uid, :title)
            RETURNING id, founder_user_id, title, created_at, updated_at
        """),
        {"uid": str(current.user_id), "title": title},
    ).mappings().first()
    db.commit()
    _log_audit(db, "create_session", current.user_id, {"title": title})
    return dict(row)


@router.get("/sessions")
async def list_sessions(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    rows = db.execute(
        text("""
            SELECT id, founder_user_id, title, created_at, updated_at
            FROM founder_chat_sessions
            WHERE founder_user_id = :uid
            ORDER BY updated_at DESC
            LIMIT 100
        """),
        {"uid": str(current.user_id)},
    ).mappings().all()
    return {"sessions": [dict(r) for r in rows]}


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    _get_session_or_404(db, session_id, current.user_id)
    user_text = str(payload.get("content") or "").strip()
    if not user_text:
        raise HTTPException(status_code=422, detail="content is required")

    _insert_message(db, session_id, "user", user_text)

    history_rows = db.execute(
        text("""
            SELECT role, content_text FROM founder_chat_messages
            WHERE session_id = :sid ORDER BY created_at ASC LIMIT 40
        """),
        {"sid": str(session_id)},
    ).mappings().all()

    history_text = "\n".join(
        f"{r['role'].upper()}: {r['content_text'] or ''}" for r in history_rows
    )

    try:
        svc = AiService()
        assistant_text, meta = svc.chat(
            system=_SYSTEM_PROMPT,
            user=history_text,
            max_tokens=4096,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {exc}")

    action_plan = _parse_action_plan(assistant_text)
    display_text = assistant_text
    if action_plan:
        start = assistant_text.find("```action_plan")
        display_text = assistant_text[:start].strip()

    msg = _insert_message(db, session_id, "assistant", display_text, content_json=action_plan)

    db.execute(
        text("UPDATE founder_chat_sessions SET updated_at = now() WHERE id = :sid"),
        {"sid": str(session_id)},
    )
    db.commit()

    return {
        "message": msg,
        "action_plan": action_plan,
        "ai_meta": meta,
    }


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    _get_session_or_404(db, session_id, current.user_id)
    rows = db.execute(
        text("""
            SELECT id, session_id, role, content_text, content_json, created_at
            FROM founder_chat_messages
            WHERE session_id = :sid
            ORDER BY created_at ASC
        """),
        {"sid": str(session_id)},
    ).mappings().all()
    return {"messages": [dict(r) for r in rows]}


@router.post("/sessions/{session_id}/runs/propose")
async def propose_run(
    session_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    _get_session_or_404(db, session_id, current.user_id)
    plan_json = payload.get("plan") or {}
    if not plan_json:
        raise HTTPException(status_code=422, detail="plan is required")

    row = db.execute(
        text("""
            INSERT INTO founder_chat_runs (session_id, status, plan_json)
            VALUES (:sid, 'proposed', :plan::jsonb)
            RETURNING id, session_id, status, plan_json, created_at, updated_at
        """),
        {"sid": str(session_id), "plan": json.dumps(plan_json)},
    ).mappings().first()
    db.commit()

    run = dict(row)
    actions = plan_json.get("actions") or []
    for action in actions:
        db.execute(
            text("""
                INSERT INTO founder_chat_actions (run_id, action_type, payload_json, status)
                VALUES (:rid, :atype, :payload::jsonb, 'proposed')
            """),
            {"rid": str(run["id"]), "atype": action.get("type", "UNKNOWN"), "payload": json.dumps(action.get("payload", {}))},
        )
    db.commit()

    _log_audit(db, "propose_run", current.user_id, {"run_id": str(run["id"]), "plan_summary": plan_json.get("summary")})
    return run


@router.post("/runs/{run_id}/execute")
async def execute_run(
    run_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    run = _get_run_or_404(db, run_id, current.user_id)
    if run["status"] not in ("proposed", "blocked"):
        raise HTTPException(status_code=422, detail=f"Cannot execute run in status '{run['status']}'")

    settings = get_settings()
    gh_token = getattr(settings, "github_token", "") or ""
    gh_repo = getattr(settings, "github_repo", "") or "FusionEMS-Core"
    gh_owner = getattr(settings, "github_owner", "") or ""
    ref = payload.get("ref") or "verdent-upgrades"

    gh_run_id = None
    gh_run_url = None

    if gh_token and gh_owner:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.github.com/repos/{gh_owner}/{gh_repo}/actions/workflows/release-gate.yml/dispatches",
                    headers={
                        "Authorization": f"Bearer {gh_token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={"ref": ref, "inputs": {"run_id": str(run_id), "stage": "stage"}},
                )
                if resp.status_code == 204:
                    await _poll_gh_run_id(client, gh_owner, gh_repo, gh_token, run_id, db)
                else:
                    logger.warning("gh_dispatch_failed status=%s body=%s", resp.status_code, resp.text[:300])
        except Exception as exc:
            logger.warning("gh_dispatch_error run_id=%s err=%s", run_id, exc)
    else:
        logger.info("github_not_configured — marking run as running (manual execution required)")

    db.execute(
        text("""
            UPDATE founder_chat_runs
            SET status = 'running', updated_at = now(),
                gh_run_id = :ghid, gh_run_url = :ghurl
            WHERE id = :rid
        """),
        {"rid": str(run_id), "ghid": gh_run_id, "ghurl": gh_run_url},
    )
    db.commit()

    _log_audit(db, "execute_run", current.user_id, {"run_id": str(run_id), "ref": ref})
    return {"run_id": str(run_id), "status": "running", "gh_run_id": gh_run_id, "gh_run_url": gh_run_url}


async def _poll_gh_run_id(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    token: str,
    run_id: uuid.UUID,
    db: Session,
) -> None:
    import asyncio
    await asyncio.sleep(3)
    try:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/runs",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"per_page": 5, "event": "workflow_dispatch"},
        )
        if resp.status_code == 200:
            runs = resp.json().get("workflow_runs", [])
            if runs:
                latest = runs[0]
                db.execute(
                    text("UPDATE founder_chat_runs SET gh_run_id = :ghid, gh_run_url = :ghurl WHERE id = :rid"),
                    {"ghid": str(latest["id"]), "ghurl": latest.get("html_url"), "rid": str(run_id)},
                )
    except Exception as exc:
        logger.warning("poll_gh_run_id_failed err=%s", exc)


@router.get("/runs/{run_id}")
async def get_run(
    run_id: uuid.UUID,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    run = _get_run_or_404(db, run_id, current.user_id)
    actions = db.execute(
        text("""
            SELECT id, run_id, action_type, payload_json, status, result_json, created_at
            FROM founder_chat_actions WHERE run_id = :rid ORDER BY created_at ASC
        """),
        {"rid": str(run_id)},
    ).mappings().all()
    return {"run": run, "actions": [dict(a) for a in actions]}


@router.post("/runs/{run_id}/approve")
async def approve_run(
    run_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    run = _get_run_or_404(db, run_id, current.user_id)
    gate = run.get("release_gate_results_json") or {}
    blockers = [k for k, v in gate.items() if v is False] if isinstance(gate, dict) else []

    if not payload.get("force") and run["status"] not in ("passed",):
        raise HTTPException(
            status_code=422,
            detail=f"Run status is '{run['status']}'. Must be 'passed' before approving. Pass force=true to override.",
        )
    if not payload.get("force") and blockers:
        raise HTTPException(
            status_code=422,
            detail=f"Release gates failed: {blockers}. Fix all blockers before approving.",
        )

    db.execute(
        text("UPDATE founder_chat_runs SET status = 'approved', updated_at = now() WHERE id = :rid"),
        {"rid": str(run_id)},
    )
    db.commit()
    _log_audit(db, "approve_run", current.user_id, {"run_id": str(run_id), "force": bool(payload.get("force"))})
    return {"run_id": str(run_id), "status": "approved"}


@router.post("/runs/{run_id}/merge")
async def merge_run(
    run_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    run = _get_run_or_404(db, run_id, current.user_id)
    if run["status"] != "approved":
        raise HTTPException(status_code=422, detail="Run must be approved before merging")

    db.execute(
        text("UPDATE founder_chat_runs SET status = 'merged', updated_at = now() WHERE id = :rid"),
        {"rid": str(run_id)},
    )
    db.commit()
    _log_audit(db, "merge_run", current.user_id, {"run_id": str(run_id)})
    return {"run_id": str(run_id), "status": "merged"}


@router.post("/runs/{run_id}/gate-result")
async def post_gate_result(
    run_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(db_session_dependency),
):
    settings = get_settings()
    token = request.headers.get("X-Gate-Token", "")
    expected = getattr(settings, "internal_worker_secret", "") or ""
    if expected and token != expected:
        raise HTTPException(status_code=403, detail="Invalid gate token")

    results = payload.get("results") or {}
    all_passed = all(v is True for v in results.values()) if results else False
    new_status = "passed" if all_passed else "blocked"

    db.execute(
        text("""
            UPDATE founder_chat_runs
            SET status = :status, release_gate_results_json = :results::jsonb,
                gh_run_id = COALESCE(:ghid, gh_run_id),
                gh_run_url = COALESCE(:ghurl, gh_run_url),
                updated_at = now()
            WHERE id = :rid
        """),
        {
            "rid": str(run_id),
            "status": new_status,
            "results": json.dumps(results),
            "ghid": payload.get("gh_run_id"),
            "ghurl": payload.get("gh_run_url"),
        },
    )
    db.commit()
    return {"run_id": str(run_id), "status": new_status}
