from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/templates", tags=["Template Builder"])


class TemplateCreate(BaseModel):
    name: str
    category: str = "general"
    format: str = "html"
    content: str = ""
    variables: list[str] = Field(default_factory=list)
    conditional_blocks: list[dict] = Field(default_factory=list)
    compliance_phrases: list[str] = Field(default_factory=list)
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    security_classification: str = "standard"
    role_visibility: list[str] = Field(default_factory=list)
    branding: dict = Field(default_factory=dict)
    region: str = ""
    module: str = ""
    is_locked: bool = False
    requires_approval: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    variables: list[str] | None = None
    conditional_blocks: list[dict] | None = None
    tags: list[str] | None = None
    is_locked: bool | None = None
    branding: dict | None = None
    language: str | None = None
    security_classification: str | None = None


class VariableInjectionRequest(BaseModel):
    template_id: uuid.UUID
    variable_map: dict[str, Any]
    preview_only: bool = False


class TemplateApprovalRequest(BaseModel):
    template_id: uuid.UUID
    action: str
    notes: str = ""


class TemplateCloneRequest(BaseModel):
    template_id: uuid.UUID
    new_name: str
    plan_tier: str = "standard"


class TemplateDiffRequest(BaseModel):
    template_id: uuid.UUID
    version_a: int
    version_b: int


class BulkGenerateRequest(BaseModel):
    template_id: uuid.UUID
    records: list[dict]
    output_format: str = "pdf"


class ABTestRequest(BaseModel):
    template_a_id: uuid.UUID
    template_b_id: uuid.UUID
    test_name: str


@router.post("")
async def create_template(
    body: TemplateCreate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems"])
    svc = DominationService(db, get_event_publisher())
    data = body.model_dump()
    data["status"] = "draft"
    data["created_by"] = str(current.user_id)
    data["version"] = 1
    record = await svc.create(
        table="templates",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=data,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.get("")
async def list_templates(
    category: str | None = None,
    language: str | None = None,
    tag: str | None = None,
    security_classification: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems", "viewer"])
    svc = DominationService(db, get_event_publisher())
    all_templates = svc.repo("templates").list(tenant_id=current.tenant_id, limit=5000)
    results = []
    for t in all_templates:
        d = t.get("data", {})
        if category and d.get("category") != category:
            continue
        if language and d.get("language") != language:
            continue
        if tag and tag not in d.get("tags", []):
            continue
        if security_classification and d.get("security_classification") != security_classification:
            continue
        role_vis = d.get("role_visibility", [])
        if role_vis and current.role not in role_vis and current.role not in ("founder", "admin"):
            continue
        results.append(t)
    return {"templates": results, "count": len(results)}


@router.get("/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems", "viewer"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    return record


@router.patch("/{template_id}")
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    if record.get("data", {}).get("is_locked") and current.role not in ("founder", "admin"):
        raise HTTPException(status_code=403, detail="template_locked")
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    patch["version"] = record.get("data", {}).get("version", 1) + 1
    patch["updated_by"] = str(current.user_id)
    patch["updated_at"] = datetime.now(UTC).isoformat()
    updated = await svc.update(
        table="templates",
        tenant_id=current.tenant_id,
        record_id=record["id"],
        actor_user_id=current.user_id,
        expected_version=record.get("version", 1),
        patch=patch,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    history_entry = {
        "template_id": str(template_id),
        "version": patch["version"],
        "content_snapshot": patch.get("content", record.get("data", {}).get("content", "")),
        "changed_by": str(current.user_id),
        "changed_at": patch["updated_at"],
    }
    await svc.create(
        table="template_versions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=history_entry,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return updated


@router.delete("/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    await svc.update(
        table="templates",
        tenant_id=current.tenant_id,
        record_id=record["id"],
        actor_user_id=current.user_id,
        expected_version=record.get("version", 1),
        patch={"status": "archived", "archived_at": datetime.now(UTC).isoformat()},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "archived", "template_id": str(template_id)}


@router.post("/inject-variables")
async def inject_variables(
    body: VariableInjectionRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=body.template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    content = record.get("data", {}).get("content", "")
    missing_vars = []
    for var in record.get("data", {}).get("variables", []):
        if var not in body.variable_map:
            missing_vars.append(var)
    rendered = content
    for k, v in body.variable_map.items():
        rendered = rendered.replace(f"{{{{{k}}}}}", str(v))
    errors = [f"Missing variable: {v}" for v in missing_vars]
    if not body.preview_only and not errors:
        await svc.create(
            table="template_renders",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "template_id": str(body.template_id),
                "variable_map": body.variable_map,
                "rendered_length": len(rendered),
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    return {
        "rendered": rendered,
        "errors": errors,
        "preview_only": body.preview_only,
        "missing_variables": missing_vars,
    }


@router.post("/{template_id}/approve")
async def approve_template(
    template_id: uuid.UUID,
    body: TemplateApprovalRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    new_status = "approved" if body.action == "approve" else "rejected"
    updated = await svc.update(
        table="templates",
        tenant_id=current.tenant_id,
        record_id=record["id"],
        actor_user_id=current.user_id,
        expected_version=record.get("version", 1),
        patch={
            "status": new_status,
            "approval_notes": body.notes,
            "approved_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return updated


@router.post("/clone")
async def clone_template(
    body: TemplateCloneRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    source = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=body.template_id)
    if not source:
        raise HTTPException(status_code=404, detail="source_template_not_found")
    new_data = {**source.get("data", {})}
    new_data["name"] = body.new_name
    new_data["status"] = "draft"
    new_data["cloned_from"] = str(body.template_id)
    new_data["plan_tier"] = body.plan_tier
    new_data["version"] = 1
    new_data["created_by"] = str(current.user_id)
    new_data.pop("is_locked", None)
    record = await svc.create(
        table="templates",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=new_data,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.get("/{template_id}/versions")
async def template_versions(
    template_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems"])
    svc = DominationService(db, get_event_publisher())
    all_versions = svc.repo("template_versions").list(tenant_id=current.tenant_id, limit=200)
    filtered = [v for v in all_versions if v.get("data", {}).get("template_id") == str(template_id)]
    filtered.sort(key=lambda v: v.get("data", {}).get("version", 0), reverse=True)
    return {"versions": filtered}


@router.post("/{template_id}/rollback/{version}")
async def rollback_template(
    template_id: uuid.UUID,
    version: int,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    all_versions = svc.repo("template_versions").list(tenant_id=current.tenant_id, limit=500)
    target = next(
        (
            v
            for v in all_versions
            if v.get("data", {}).get("template_id") == str(template_id)
            and v.get("data", {}).get("version") == version
        ),
        None,
    )
    if not target:
        raise HTTPException(status_code=404, detail="version_not_found")
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    updated = await svc.update(
        table="templates",
        tenant_id=current.tenant_id,
        record_id=record["id"],
        actor_user_id=current.user_id,
        expected_version=record.get("version", 1),
        patch={
            "content": target.get("data", {}).get("content_snapshot", ""),
            "rolled_back_to": version,
            "version": record.get("data", {}).get("version", 1) + 1,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return updated


@router.post("/diff")
async def diff_versions(
    body: TemplateDiffRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    all_versions = svc.repo("template_versions").list(tenant_id=current.tenant_id, limit=500)
    ver_a = next(
        (
            v
            for v in all_versions
            if v.get("data", {}).get("template_id") == str(body.template_id)
            and v.get("data", {}).get("version") == body.version_a
        ),
        None,
    )
    ver_b = next(
        (
            v
            for v in all_versions
            if v.get("data", {}).get("template_id") == str(body.template_id)
            and v.get("data", {}).get("version") == body.version_b
        ),
        None,
    )
    if not ver_a or not ver_b:
        raise HTTPException(status_code=404, detail="version_not_found")
    content_a = ver_a.get("data", {}).get("content_snapshot", "")
    content_b = ver_b.get("data", {}).get("content_snapshot", "")
    lines_a = content_a.splitlines()
    lines_b = content_b.splitlines()
    added = [line for line in lines_b if line not in lines_a]
    removed = [line for line in lines_a if line not in lines_b]
    return {
        "template_id": str(body.template_id),
        "version_a": body.version_a,
        "version_b": body.version_b,
        "added_lines": added,
        "removed_lines": removed,
        "changed": content_a != content_b,
    }


@router.post("/bulk-generate")
async def bulk_generate(
    body: BulkGenerateRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=body.template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    content = record.get("data", {}).get("content", "")
    results = []
    for idx, rec in enumerate(body.records):
        rendered = content
        for k, v in rec.items():
            rendered = rendered.replace(f"{{{{{k}}}}}", str(v))
        results.append({"index": idx, "rendered_length": len(rendered), "status": "generated"})
    job = await svc.create(
        table="bulk_generation_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "template_id": str(body.template_id),
            "output_format": body.output_format,
            "record_count": len(body.records),
            "status": "completed",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"job": job, "results": results, "total": len(results)}


@router.post("/ab-test")
async def create_ab_test(
    body: ABTestRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    test = await svc.create(
        table="template_ab_tests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "template_a_id": str(body.template_a_id),
            "template_b_id": str(body.template_b_id),
            "test_name": body.test_name,
            "status": "active",
            "impressions_a": 0,
            "impressions_b": 0,
            "conversions_a": 0,
            "conversions_b": 0,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return test


@router.get("/global-variables")
async def global_variables(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems"])
    svc = DominationService(db, get_event_publisher())
    variables = svc.repo("global_variables").list(tenant_id=current.tenant_id, limit=1000)
    return {"variables": variables}


@router.post("/global-variables")
async def create_global_variable(
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    record = await svc.create(
        table="global_variables",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=body,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.post("/{template_id}/validate")
async def validate_template(
    template_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing", "ems"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    data = record.get("data", {})
    errors = []
    warnings = []
    content = data.get("content", "")
    if not content.strip():
        errors.append("Template content is empty")
    declared_vars = set(data.get("variables", []))
    used_vars = set(re.findall(r"\{\{(\w+)\}\}", content))
    undeclared = used_vars - declared_vars
    if undeclared:
        warnings.append(f"Undeclared variables used: {', '.join(undeclared)}")
    unused = declared_vars - used_vars
    if unused:
        warnings.append(f"Declared but unused variables: {', '.join(unused)}")
    return {
        "template_id": str(template_id),
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "declared_variables": list(declared_vars),
        "used_variables": list(used_vars),
    }


@router.get("/{template_id}/analytics")
async def template_analytics(
    template_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    renders = svc.repo("template_renders").list(tenant_id=current.tenant_id, limit=10000)
    template_renders = [
        r for r in renders if r.get("data", {}).get("template_id") == str(template_id)
    ]
    downloads = svc.repo("template_downloads").list(tenant_id=current.tenant_id, limit=10000)
    template_downloads = [
        d for d in downloads if d.get("data", {}).get("template_id") == str(template_id)
    ]
    return {
        "template_id": str(template_id),
        "total_renders": len(template_renders),
        "total_downloads": len(template_downloads),
        "usage_trend": "up" if len(template_renders) > 5 else "stable",
    }


@router.get("/analytics/top-performing")
async def top_performing_templates(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    renders = svc.repo("template_renders").list(tenant_id=current.tenant_id, limit=10000)
    counts: dict[str, int] = {}
    for r in renders:
        tid = r.get("data", {}).get("template_id", "unknown")
        counts[tid] = counts.get(tid, 0) + 1
    sorted_templates = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "top_templates": [{"template_id": t[0], "render_count": t[1]} for t in sorted_templates]
    }


@router.post("/{template_id}/schedule-delivery")
async def schedule_delivery(
    template_id: uuid.UUID,
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    job = await svc.create(
        table="scheduled_deliveries",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "template_id": str(template_id),
            "deliver_at": body.get("deliver_at"),
            "recipients": body.get("recipients", []),
            "delivery_method": body.get("delivery_method", "email"),
            "status": "scheduled",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return job


@router.get("/lifecycle/management")
async def lifecycle_management(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    all_templates = svc.repo("templates").list(tenant_id=current.tenant_id, limit=5000)
    now = datetime.now(UTC)
    lifecycle = {
        "total": len(all_templates),
        "draft": sum(1 for t in all_templates if t.get("data", {}).get("status") == "draft"),
        "approved": sum(1 for t in all_templates if t.get("data", {}).get("status") == "approved"),
        "archived": sum(1 for t in all_templates if t.get("data", {}).get("status") == "archived"),
        "locked": sum(1 for t in all_templates if t.get("data", {}).get("is_locked")),
        "as_of": now.isoformat(),
    }
    return lifecycle


@router.post("/{template_id}/generate-secure-link")
async def generate_secure_link(
    template_id: uuid.UUID,
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    svc = DominationService(db, get_event_publisher())
    record = svc.repo("templates").get(tenant_id=current.tenant_id, record_id=template_id)
    if not record:
        raise HTTPException(status_code=404, detail="template_not_found")
    token = hashlib.sha256(
        f"{template_id}{current.tenant_id}{datetime.now(UTC).isoformat()}".encode()
    ).hexdigest()
    link = await svc.create(
        table="template_secure_links",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "template_id": str(template_id),
            "token": token,
            "expires_at": body.get("expires_at"),
            "max_downloads": body.get("max_downloads", 1),
            "downloads": 0,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"link": link, "token": token}


@router.get("/audit-trail")
async def template_audit_trail(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    versions = svc.repo("template_versions").list(tenant_id=current.tenant_id, limit=1000)
    versions.sort(key=lambda v: v.get("created_at", ""), reverse=True)
    return {"audit_trail": versions[:100]}


@router.post("/policy-mass-refresh")
async def policy_mass_refresh(
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())
    all_templates = svc.repo("templates").list(tenant_id=current.tenant_id, limit=5000)
    policy_templates = [
        t for t in all_templates if "compliance" in t.get("data", {}).get("tags", [])
    ]
    updated_count = 0
    for t in policy_templates:
        await svc.update(
            table="templates",
            tenant_id=current.tenant_id,
            record_id=t["id"],
            actor_user_id=current.user_id,
            expected_version=t.get("version", 1),
            patch={"policy_refreshed_at": datetime.now(UTC).isoformat()},
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        updated_count += 1
    return {"refreshed_count": updated_count, "as_of": datetime.now(UTC).isoformat()}


@router.get("/dependency-map")
async def dependency_map(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    all_templates = svc.repo("templates").list(tenant_id=current.tenant_id, limit=5000)
    nodes = [
        {
            "id": t["id"],
            "name": t.get("data", {}).get("name", ""),
            "module": t.get("data", {}).get("module", ""),
        }
        for t in all_templates
    ]
    edges = []
    for t in all_templates:
        deps = t.get("data", {}).get("dependencies", [])
        for dep in deps:
            edges.append({"from": t["id"], "to": dep})
    return {"nodes": nodes, "edges": edges}
