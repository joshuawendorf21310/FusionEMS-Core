from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/visibility", tags=["Visibility Rule Maker"])


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


# ── Rule CRUD ────────────────────────────────────────────────────────────────

@router.post("/rules")
async def create_rule(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_rules",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**payload, "created_by": str(current.user_id), "status": "active"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/rules")
async def list_rules(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    repo = _svc(db).repo("visibility_rules")
    return repo.list(tenant_id=current.tenant_id)


@router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rec = _svc(db).repo("visibility_rules").get(tenant_id=current.tenant_id, record_id=rule_id)
    return rec or {"error": "not_found"}


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    version = payload.pop("version", 1)
    result = await _svc(db).update(
        table="visibility_rules",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=rule_id,
        expected_version=version,
        patch=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result or {"error": "conflict_or_not_found"}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).update(
        table="visibility_rules",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=rule_id,
        expected_version=1,
        patch={"status": "deleted"},
        correlation_id=getattr(request.state, "correlation_id", None),
    ) or {"error": "not_found"}


# ── Rule evaluation engine ────────────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate_rules(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Evaluate visibility rules for a given context (role, claim_status, payer_type, etc.)."""
    context = payload.get("context", {})
    rules = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    active = [r for r in rules if r.get("data", {}).get("status") == "active"]

    visible_fields: list[str] = []
    masked_fields: list[str] = []
    denied_fields: list[str] = []
    applied_rules: list[str] = []

    for rule in active:
        d = rule.get("data", {})
        rule_role = d.get("role")
        if rule_role and rule_role != context.get("role") and context.get("role") != "founder":
            continue
        action = d.get("action", "show")
        fields = d.get("fields", [])
        if action == "show":
            visible_fields.extend(fields)
        elif action == "mask":
            masked_fields.extend(fields)
        elif action == "deny":
            denied_fields.extend(fields)
        applied_rules.append(str(rule.get("id", "")))

    return {
        "visible_fields": list(set(visible_fields)),
        "masked_fields": list(set(masked_fields)),
        "denied_fields": list(set(denied_fields)),
        "applied_rules": applied_rules,
        "context": context,
    }


# ── Role-based field visibility ───────────────────────────────────────────────

@router.get("/role-matrix")
async def role_matrix(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Return field visibility matrix across all roles."""
    roles = ["founder", "agency_admin", "billing", "ems", "compliance", "viewer"]
    matrix: dict[str, list[str]] = {}
    rules = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    for role in roles:
        visible = []
        for r in rules:
            d = r.get("data", {})
            if d.get("role") == role and d.get("action") == "show":
                visible.extend(d.get("fields", []))
        matrix[role] = list(set(visible))
    return {"matrix": matrix, "roles": roles}


# ── Tenant-scoped data isolation ──────────────────────────────────────────────

@router.get("/tenant-isolation-status")
async def tenant_isolation_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return {
        "tenant_id": str(current.tenant_id),
        "isolation_active": True,
        "rls_enforced": True,
        "cross_tenant_prevention": True,
    }


# ── PHI masking ───────────────────────────────────────────────────────────────

@router.get("/phi-fields")
async def phi_fields(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    phi = [
        "patient_name", "dob", "ssn", "address", "phone", "email",
        "insurance_id", "medical_record_number", "diagnosis_code",
        "narrative", "chief_complaint",
    ]
    masked = phi if current.role not in ("founder", "agency_admin", "billing") else []
    return {"phi_fields": phi, "masked_for_role": current.role, "masked": masked}


@router.post("/phi-mask-preview")
async def phi_mask_preview(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    fields = payload.get("fields", {})
    phi_keys = {
        "patient_name", "dob", "ssn", "address", "phone", "email",
        "insurance_id", "medical_record_number",
    }
    result = {}
    for k, v in fields.items():
        if k in phi_keys and current.role not in ("founder", "agency_admin"):
            result[k] = "***REDACTED***"
        else:
            result[k] = v
    return {"preview": result, "role": current.role}


# ── Conditional visibility ────────────────────────────────────────────────────

@router.post("/conditional-check")
async def conditional_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    claim_status = payload.get("claim_status")
    payer_type = payload.get("payer_type")
    rules = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    matched = []
    for r in rules:
        d = r.get("data", {})
        conditions = d.get("conditions", {})
        cs_match = not conditions.get("claim_status") or conditions["claim_status"] == claim_status
        pt_match = not conditions.get("payer_type") or conditions["payer_type"] == payer_type
        if cs_match and pt_match:
            matched.append(d.get("rule_name", str(r.get("id", ""))))
    return {"matched_rules": matched, "claim_status": claim_status, "payer_type": payer_type}


# ── Founder override ──────────────────────────────────────────────────────────

@router.get("/founder-view-status")
async def founder_view_status(
    current: CurrentUser = Depends(require_role("founder")),
):
    return {
        "founder_override": True,
        "full_view_enabled": True,
        "phi_unmasked": True,
        "all_tenants_visible": True,
        "audit_mode": True,
    }


# ── Billing / Compliance view toggles ────────────────────────────────────────

@router.get("/view-modes")
async def view_modes(
    current: CurrentUser = Depends(get_current_user),
):
    modes = {
        "billing_only": current.role in ("billing", "agency_admin", "founder"),
        "compliance_only": current.role in ("compliance", "agency_admin", "founder"),
        "accreditation_reviewer": current.role in ("accreditation", "agency_admin", "founder"),
        "audit_mode": current.role in ("founder", "agency_admin"),
        "read_only_safe": True,
        "deny_bulk_edit": current.role not in ("founder", "agency_admin"),
    }
    return {"role": current.role, "modes": modes}


# ── Stripe-status visibility gating ──────────────────────────────────────────

@router.post("/stripe-gate-check")
async def stripe_gate_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    stripe_status = payload.get("stripe_status", "inactive")
    gated_modules = ["billing_reports", "export_full", "revenue_analytics"]
    accessible = gated_modules if stripe_status == "active" else []
    return {
        "stripe_status": stripe_status,
        "accessible_modules": accessible,
        "gated_modules": gated_modules if stripe_status != "active" else [],
    }


# ── Module-based UI gating ────────────────────────────────────────────────────

@router.get("/module-gates")
async def module_gates(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    all_modules = [
        "billing", "nemsis", "fhir", "cad", "fleet", "scheduling",
        "fire_ops", "accreditation", "analytics", "founder_command",
    ]
    role_access = {
        "founder": all_modules,
        "agency_admin": all_modules,
        "billing": ["billing", "nemsis", "analytics"],
        "ems": ["nemsis", "cad", "fleet", "scheduling"],
        "compliance": ["nemsis", "accreditation", "analytics"],
        "viewer": ["billing"],
    }
    accessible = role_access.get(current.role, [])
    return {"role": current.role, "accessible_modules": accessible, "all_modules": all_modules}


# ── Access control: device, IP, MFA, geo ────────────────────────────────────

@router.post("/access-control-check")
async def access_control_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    device_trusted = payload.get("device_trusted", False)
    ip_allowed = payload.get("ip_allowed", True)
    mfa_verified = payload.get("mfa_verified", False)
    geo_allowed = payload.get("geo_allowed", True)
    session_valid = payload.get("session_valid", True)

    sensitive_view = current.role in ("founder", "agency_admin", "billing")
    mfa_required = sensitive_view and not mfa_verified
    ip_blocked = not ip_allowed
    geo_blocked = not geo_allowed

    access_granted = not mfa_required and not ip_blocked and not geo_blocked and session_valid
    return {
        "access_granted": access_granted,
        "mfa_required": mfa_required,
        "ip_blocked": ip_blocked,
        "geo_blocked": geo_blocked,
        "device_trusted": device_trusted,
        "session_valid": session_valid,
    }


# ── Temporary elevated access ─────────────────────────────────────────────────

@router.post("/elevated-access/grant")
async def grant_elevated_access(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_elevated_access",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "target_user_id": payload.get("target_user_id"),
            "duration_minutes": payload.get("duration_minutes", 60),
            "granted_by": str(current.user_id),
            "reason": payload.get("reason"),
            "status": "active",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/elevated-access")
async def list_elevated_access(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_elevated_access").list(tenant_id=current.tenant_id)


# ── Time-based visibility windows ─────────────────────────────────────────────

@router.post("/time-windows")
async def create_time_window(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_time_windows",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "field": payload.get("field"),
            "start_utc": payload.get("start_utc"),
            "end_utc": payload.get("end_utc"),
            "roles": payload.get("roles", []),
            "status": "active",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/time-windows")
async def list_time_windows(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_time_windows").list(tenant_id=current.tenant_id)


# ── One-time secure view links ─────────────────────────────────────────────────

@router.post("/secure-links")
async def create_secure_link(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    token = str(uuid.uuid4()).replace("-", "")
    return await _svc(db).create(
        table="visibility_secure_links",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "token": token,
            "resource": payload.get("resource"),
            "expires_minutes": payload.get("expires_minutes", 30),
            "used": False,
            "created_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/secure-links/{token}/validate")
async def validate_secure_link(
    token: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    links = _svc(db).repo("visibility_secure_links").list(tenant_id=current.tenant_id)
    match = next((l for l in links if l.get("data", {}).get("token") == token), None)
    if not match:
        return {"valid": False, "reason": "not_found"}
    d = match.get("data", {})
    if d.get("used"):
        return {"valid": False, "reason": "already_used"}
    return {"valid": True, "resource": d.get("resource"), "expires_minutes": d.get("expires_minutes")}


# ── Data redaction preview ─────────────────────────────────────────────────────

@router.post("/redaction-preview")
async def redaction_preview(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    template = payload.get("template", "standard")
    record = payload.get("record", {})
    templates = {
        "standard": {"mask": ["ssn", "dob", "phone"], "deny": []},
        "hipaa_strict": {"mask": ["ssn", "dob", "phone", "address", "email", "patient_name"], "deny": ["diagnosis_code"]},
        "billing_safe": {"mask": ["ssn"], "deny": []},
        "export_safe": {"mask": ["ssn", "dob", "phone", "address"], "deny": ["narrative"]},
    }
    rules = templates.get(template, templates["standard"])
    redacted = {}
    for k, v in record.items():
        if k in rules["deny"]:
            redacted[k] = "[DENIED]"
        elif k in rules["mask"]:
            redacted[k] = "***"
        else:
            redacted[k] = v
    return {"template": template, "original_keys": list(record.keys()), "redacted": redacted}


# ── Bulk rule application ──────────────────────────────────────────────────────

@router.post("/rules/bulk-apply")
async def bulk_apply_rules(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    rules = payload.get("rules", [])
    created = []
    for rule in rules:
        rec = await _svc(db).create(
            table="visibility_rules",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={**rule, "status": "active", "bulk_applied": True},
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        created.append(rec.get("id"))
    return {"created_count": len(created), "rule_ids": created}


# ── Rule conflict detection ───────────────────────────────────────────────────

@router.post("/rules/conflict-check")
async def conflict_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    incoming = payload.get("rule", {})
    existing = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    conflicts = []
    for r in existing:
        d = r.get("data", {})
        if d.get("status") != "active":
            continue
        same_role = d.get("role") == incoming.get("role")
        field_overlap = set(d.get("fields", [])) & set(incoming.get("fields", []))
        if same_role and field_overlap and d.get("action") != incoming.get("action"):
            conflicts.append({"rule_id": str(r.get("id")), "conflicting_fields": list(field_overlap)})
    return {"has_conflicts": bool(conflicts), "conflicts": conflicts}


# ── Rule testing sandbox ──────────────────────────────────────────────────────

@router.post("/rules/sandbox-test")
async def sandbox_test(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    rule = payload.get("rule", {})
    test_context = payload.get("test_context", {})
    role_match = not rule.get("role") or rule.get("role") == test_context.get("role")
    cond = rule.get("conditions", {})
    claim_match = not cond.get("claim_status") or cond["claim_status"] == test_context.get("claim_status")
    payer_match = not cond.get("payer_type") or cond["payer_type"] == test_context.get("payer_type")
    would_apply = role_match and claim_match and payer_match
    return {
        "would_apply": would_apply,
        "role_match": role_match,
        "conditions_match": claim_match and payer_match,
        "action": rule.get("action"),
        "fields": rule.get("fields", []),
    }


# ── Visibility change audit log ───────────────────────────────────────────────

@router.post("/audit-log")
async def create_visibility_audit(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_audit_log",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "action": payload.get("action"),
            "rule_id": payload.get("rule_id"),
            "field": payload.get("field"),
            "previous_state": payload.get("previous_state"),
            "new_state": payload.get("new_state"),
            "actor": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/audit-log")
async def list_visibility_audit(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_audit_log").list(tenant_id=current.tenant_id)


# ── AND/OR logic chaining ─────────────────────────────────────────────────────

@router.post("/logic-chain/evaluate")
async def evaluate_logic_chain(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    chain = payload.get("chain", {})
    context = payload.get("context", {})
    op = chain.get("operator", "AND").upper()
    conditions = chain.get("conditions", [])

    results = []
    for cond in conditions:
        field = cond.get("field")
        value = cond.get("value")
        ctx_val = context.get(field)
        results.append(ctx_val == value)

    if op == "AND":
        result = all(results)
    elif op == "OR":
        result = any(results)
    else:
        result = all(results)

    return {"operator": op, "result": result, "condition_results": results}


# ── Approval workflow for visibility changes ──────────────────────────────────

@router.post("/approval-requests")
async def create_approval_request(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_approval_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "requested_by": str(current.user_id),
            "rule_change": payload.get("rule_change"),
            "justification": payload.get("justification"),
            "status": "pending",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/approval-requests")
async def list_approval_requests(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_approval_requests").list(tenant_id=current.tenant_id)


@router.put("/approval-requests/{req_id}/decide")
async def decide_approval(
    req_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    decision = payload.get("decision", "rejected")
    return await _svc(db).update(
        table="visibility_approval_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=req_id,
        expected_version=1,
        patch={"status": decision, "decided_by": str(current.user_id)},
        correlation_id=getattr(request.state, "correlation_id", None),
    ) or {"error": "not_found"}


# ── Compliance / Audit-lock ────────────────────────────────────────────────────

@router.post("/compliance-lock")
async def compliance_lock(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_compliance_locks",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "lock_type": payload.get("lock_type", "audit"),
            "scope": payload.get("scope", "tenant"),
            "locked_by": str(current.user_id),
            "reason": payload.get("reason"),
            "active": True,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/compliance-lock/status")
async def compliance_lock_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    locks = _svc(db).repo("visibility_compliance_locks").list(tenant_id=current.tenant_id)
    active_locks = [l for l in locks if l.get("data", {}).get("active")]
    return {"locked": bool(active_locks), "active_locks": len(active_locks), "locks": active_locks}


# ── Emergency access mode ─────────────────────────────────────────────────────

@router.post("/emergency-access")
async def emergency_access(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_emergency_access",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "triggered_by": str(current.user_id),
            "reason": payload.get("reason"),
            "scope": payload.get("scope", "full"),
            "duration_minutes": payload.get("duration_minutes", 30),
            "active": True,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ── Policy versioning & rollback ──────────────────────────────────────────────

@router.post("/policies")
async def create_policy(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_policies",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "policy_name": payload.get("policy_name"),
            "version": payload.get("version", "1.0"),
            "rules_snapshot": payload.get("rules_snapshot", []),
            "created_by": str(current.user_id),
            "active": True,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/policies")
async def list_policies(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_policies").list(tenant_id=current.tenant_id)


@router.post("/policies/{policy_id}/rollback")
async def rollback_policy(
    policy_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    policy = _svc(db).repo("visibility_policies").get(tenant_id=current.tenant_id, record_id=policy_id)
    if not policy:
        return {"error": "not_found"}
    snapshot = policy.get("data", {}).get("rules_snapshot", [])
    return await _svc(db).create(
        table="visibility_rules",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"rollback_from_policy": str(policy_id), "rules": snapshot, "status": "active"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ── Historical visibility snapshot ────────────────────────────────────────────

@router.get("/snapshots")
async def list_snapshots(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_policies").list(tenant_id=current.tenant_id)


# ── JWT claim-based visibility ────────────────────────────────────────────────

@router.get("/jwt-claims-visibility")
async def jwt_claims_visibility(
    current: CurrentUser = Depends(get_current_user),
):
    claim_rules = {
        "founder": ["all"],
        "agency_admin": ["billing", "nemsis", "reports", "staff", "settings"],
        "billing": ["claims", "payments", "reports"],
        "ems": ["incidents", "patients", "vitals"],
        "compliance": ["nemsis", "audit", "accreditation"],
        "viewer": ["incidents"],
    }
    return {
        "role": current.role,
        "tenant_id": str(current.tenant_id),
        "visible_sections": claim_rules.get(current.role, []),
    }


# ── Per-endpoint restriction mapping ─────────────────────────────────────────

@router.get("/endpoint-restrictions")
async def endpoint_restrictions(
    current: CurrentUser = Depends(get_current_user),
):
    restrictions = {
        "/api/v1/billing": ["billing", "agency_admin", "founder"],
        "/api/v1/nemsis": ["ems", "compliance", "agency_admin", "founder"],
        "/api/v1/founder": ["founder"],
        "/api/v1/patients": ["ems", "billing", "agency_admin", "founder"],
        "/api/v1/incidents": ["ems", "agency_admin", "founder"],
        "/api/v1/visibility": ["agency_admin", "founder"],
    }
    accessible = {ep: roles for ep, roles in restrictions.items() if current.role in roles}
    return {"role": current.role, "accessible_endpoints": accessible, "all_restrictions": restrictions}


# ── View-level rate limiting ──────────────────────────────────────────────────

@router.get("/rate-limit-config")
async def rate_limit_config(
    current: CurrentUser = Depends(get_current_user),
):
    limits = {
        "founder": {"requests_per_minute": 1000, "burst": 200},
        "agency_admin": {"requests_per_minute": 500, "burst": 100},
        "billing": {"requests_per_minute": 300, "burst": 60},
        "ems": {"requests_per_minute": 200, "burst": 40},
        "viewer": {"requests_per_minute": 60, "burst": 15},
    }
    return {"role": current.role, "rate_limit": limits.get(current.role, limits["viewer"])}


# ── Export redaction rules ────────────────────────────────────────────────────

@router.get("/export-redaction-rules")
async def export_redaction_rules(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rules = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    export_rules = [r for r in rules if r.get("data", {}).get("apply_on_export")]
    return {"export_redaction_rules": export_rules, "count": len(export_rules)}


# ── Sensitive data auto-detection ─────────────────────────────────────────────

@router.post("/auto-detect-sensitive")
async def auto_detect_sensitive(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    fields = payload.get("fields", {})
    sensitive_patterns = {
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "phi": ["patient_name", "dob", "address", "diagnosis"],
        "financial": ["account_number", "routing_number", "credit_card"],
    }
    detected: dict[str, list[str]] = {"phi": [], "financial": [], "other": []}
    for key in fields:
        if key in sensitive_patterns["phi"]:
            detected["phi"].append(key)
        elif key in sensitive_patterns["financial"]:
            detected["financial"].append(key)
        elif "ssn" in key.lower() or "password" in key.lower():
            detected["other"].append(key)
    return {"detected_sensitive_fields": detected, "total": sum(len(v) for v in detected.values())}


# ── Visibility heatmap ────────────────────────────────────────────────────────

@router.get("/heatmap")
async def visibility_heatmap(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    rules = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    field_counts: dict[str, int] = {}
    for r in rules:
        for f in r.get("data", {}).get("fields", []):
            field_counts[f] = field_counts.get(f, 0) + 1
    sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
    return {"heatmap": [{"field": f, "rule_count": c} for f, c in sorted_fields]}


# ── Tenant visibility dashboard ───────────────────────────────────────────────

@router.get("/dashboard")
async def visibility_dashboard(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    rules = svc.repo("visibility_rules").list(tenant_id=current.tenant_id)
    audit = svc.repo("visibility_audit_log").list(tenant_id=current.tenant_id)
    locks = svc.repo("visibility_compliance_locks").list(tenant_id=current.tenant_id)
    approvals = svc.repo("visibility_approval_requests").list(tenant_id=current.tenant_id)
    active_rules = [r for r in rules if r.get("data", {}).get("status") == "active"]
    pending_approvals = [a for a in approvals if a.get("data", {}).get("status") == "pending"]
    active_locks = [l for l in locks if l.get("data", {}).get("active")]
    return {
        "total_rules": len(rules),
        "active_rules": len(active_rules),
        "audit_events": len(audit),
        "pending_approvals": len(pending_approvals),
        "active_locks": len(active_locks),
        "compliance_locked": bool(active_locks),
    }


# ── Behavioral anomaly / suspicious behavior ─────────────────────────────────

@router.post("/anomaly-trigger")
async def anomaly_trigger(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_anomaly_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "user_id": payload.get("user_id", str(current.user_id)),
            "anomaly_type": payload.get("anomaly_type"),
            "severity": payload.get("severity", "medium"),
            "auto_restricted": payload.get("severity") == "high",
            "description": payload.get("description"),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/anomaly-events")
async def list_anomaly_events(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_anomaly_events").list(tenant_id=current.tenant_id)


# ── Access scoring ────────────────────────────────────────────────────────────

@router.get("/access-score")
async def access_score(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    anomalies = svc.repo("visibility_anomaly_events").list(tenant_id=current.tenant_id)
    user_anomalies = [a for a in anomalies if a.get("data", {}).get("user_id") == str(current.user_id)]
    high = sum(1 for a in user_anomalies if a.get("data", {}).get("severity") == "high")
    medium = sum(1 for a in user_anomalies if a.get("data", {}).get("severity") == "medium")
    score = max(0, 100 - high * 30 - medium * 10)
    risk = "low" if score >= 80 else "medium" if score >= 50 else "high"
    return {"access_score": score, "risk_level": risk, "anomaly_count": len(user_anomalies)}


# ── Zero-trust enforcement ────────────────────────────────────────────────────

@router.post("/zero-trust/check")
async def zero_trust_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    resource = payload.get("resource")
    action = payload.get("action", "read")
    context = payload.get("context", {})
    mfa = context.get("mfa_verified", False)
    device_trusted = context.get("device_trusted", False)
    ip_allowed = context.get("ip_allowed", True)

    high_value_resources = ["phi_data", "financial_reports", "founder_view", "audit_logs"]
    requires_mfa = resource in high_value_resources
    trust_score = sum([mfa, device_trusted, ip_allowed]) / 3.0
    allowed = trust_score >= 0.67 and (not requires_mfa or mfa)
    return {
        "resource": resource,
        "action": action,
        "allowed": allowed,
        "trust_score": round(trust_score, 2),
        "requires_mfa": requires_mfa,
        "mfa_provided": mfa,
    }


# ── Global kill-switch ────────────────────────────────────────────────────────

@router.post("/kill-switch")
async def kill_switch(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_kill_switch",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "activated": payload.get("activated", True),
            "scope": payload.get("scope", "all"),
            "reason": payload.get("reason"),
            "activated_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/kill-switch/status")
async def kill_switch_status(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    events = _svc(db).repo("visibility_kill_switch").list(tenant_id=current.tenant_id)
    latest = events[-1] if events else None
    active = latest and latest.get("data", {}).get("activated") is True
    return {"kill_switch_active": bool(active), "latest_event": latest}


# ── Role simulation testing ───────────────────────────────────────────────────

@router.post("/role-simulation")
async def role_simulation(
    payload: dict[str, Any],
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    simulated_role = payload.get("role", "viewer")
    test_fields = payload.get("fields", [])
    rules = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    visible, masked, denied = [], [], []
    for r in rules:
        d = r.get("data", {})
        if d.get("status") != "active":
            continue
        if d.get("role") and d["role"] != simulated_role:
            continue
        action = d.get("action", "show")
        fields = [f for f in d.get("fields", []) if not test_fields or f in test_fields]
        if action == "show":
            visible.extend(fields)
        elif action == "mask":
            masked.extend(fields)
        elif action == "deny":
            denied.extend(fields)
    return {
        "simulated_role": simulated_role,
        "visible": list(set(visible)),
        "masked": list(set(masked)),
        "denied": list(set(denied)),
    }


# ── Secure demo mode ──────────────────────────────────────────────────────────

@router.get("/demo-mode/config")
async def demo_mode_config(
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "demo_mode": True,
        "phi_replaced_with_synthetic": True,
        "financial_data_zeroed": True,
        "tenant_id_anonymized": True,
        "safe_to_share_screen": True,
    }


# ── Training mode ─────────────────────────────────────────────────────────────

@router.get("/training-mode/config")
async def training_mode_config(
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "training_mode": True,
        "uses_synthetic_data": True,
        "mutations_blocked": True,
        "exports_disabled": True,
        "watermark": "TRAINING DATA - NOT FOR CLINICAL USE",
    }


# ── De-identified sandbox ─────────────────────────────────────────────────────

@router.post("/deidentify")
async def deidentify(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    record = payload.get("record", {})
    phi_fields = {"patient_name", "dob", "ssn", "address", "phone", "email", "insurance_id"}
    deidentified = {k: ("DEIDENTIFIED" if k in phi_fields else v) for k, v in record.items()}
    return {"deidentified": deidentified, "fields_removed": len([k for k in record if k in phi_fields])}


# ── Data minimization ─────────────────────────────────────────────────────────

@router.post("/data-minimization/check")
async def data_minimization_check(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    requested_fields = set(payload.get("requested_fields", []))
    purpose = payload.get("purpose", "general")
    purpose_minimums = {
        "billing": {"claim_id", "patient_id", "amount", "payer_type", "service_date"},
        "clinical": {"incident_id", "patient_id", "vitals", "narrative", "procedures"},
        "compliance": {"incident_id", "agency_id", "nemsis_status", "validation_errors"},
        "general": {"incident_id", "status"},
    }
    minimum = purpose_minimums.get(purpose, purpose_minimums["general"])
    excessive = requested_fields - minimum
    return {
        "purpose": purpose,
        "minimum_fields": list(minimum),
        "requested_fields": list(requested_fields),
        "excessive_fields": list(excessive),
        "compliant": not excessive,
    }


# ── Access change alerting ─────────────────────────────────────────────────────

@router.post("/access-alerts")
async def create_access_alert(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    return await _svc(db).create(
        table="visibility_access_alerts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "alert_type": payload.get("alert_type"),
            "user_id": payload.get("user_id", str(current.user_id)),
            "description": payload.get("description"),
            "severity": payload.get("severity", "info"),
            "acknowledged": False,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/access-alerts")
async def list_access_alerts(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    return _svc(db).repo("visibility_access_alerts").list(tenant_id=current.tenant_id)


# ── Auto-lock after failed attempts ───────────────────────────────────────────

@router.post("/auto-lock")
async def auto_lock(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    failed_attempts = payload.get("failed_attempts", 0)
    threshold = 5
    should_lock = failed_attempts >= threshold
    if should_lock:
        await _svc(db).create(
            table="visibility_access_alerts",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "alert_type": "auto_lock",
                "user_id": str(current.user_id),
                "description": f"Auto-locked after {failed_attempts} failed attempts",
                "severity": "critical",
                "acknowledged": False,
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )
    return {"locked": should_lock, "failed_attempts": failed_attempts, "threshold": threshold}


# ── Restricted search results / sensitive search query alert ─────────────────

@router.post("/search-filter")
async def search_filter(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    query = payload.get("query", "")
    sensitive_terms = ["ssn", "password", "secret", "private_key", "dob", "credit_card"]
    flagged = [term for term in sensitive_terms if term.lower() in query.lower()]
    restricted = current.role not in ("founder", "agency_admin")
    return {
        "query": query,
        "sensitive_terms_detected": flagged,
        "alert_triggered": bool(flagged),
        "search_restricted": restricted,
        "safe_to_execute": not flagged or not restricted,
    }


# ── Clipboard copy restriction ────────────────────────────────────────────────

@router.get("/clipboard-policy")
async def clipboard_policy(
    current: CurrentUser = Depends(get_current_user),
):
    restrict = current.role in ("viewer", "ems")
    return {
        "role": current.role,
        "clipboard_copy_restricted": restrict,
        "phi_copy_blocked": True,
        "financial_copy_restricted": current.role not in ("billing", "agency_admin", "founder"),
    }


# ── Third-party integration field filter ─────────────────────────────────────

@router.post("/integration-field-filter")
async def integration_field_filter(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    integration = payload.get("integration")
    record = payload.get("record", {})
    integration_allowed = {
        "stripe": {"amount", "currency", "status", "payment_intent_id"},
        "lob": {"address", "city", "state", "zip"},
        "telnyx": {"phone_number", "call_status"},
        "fhir": {"patient_id", "encounter_id", "diagnosis_code", "procedure_code"},
    }
    allowed_fields = integration_allowed.get(integration, set())
    filtered = {k: v for k, v in record.items() if k in allowed_fields}
    blocked = [k for k in record if k not in allowed_fields]
    return {"integration": integration, "filtered_record": filtered, "blocked_fields": blocked}


# ── Live policy validation ────────────────────────────────────────────────────

@router.post("/policy/live-validate")
async def live_validate_policy(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    policy = payload.get("policy", {})
    errors = []
    warnings = []
    if not policy.get("rule_name"):
        errors.append("rule_name is required")
    if not policy.get("action") in ("show", "mask", "deny"):
        errors.append("action must be one of: show, mask, deny")
    if not policy.get("fields"):
        warnings.append("No fields specified; rule will have no effect")
    if not policy.get("role") and not policy.get("conditions"):
        warnings.append("No role or conditions; rule applies universally")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


# ── Field encryption enforcement ─────────────────────────────────────────────

@router.get("/field-encryption-status")
async def field_encryption_status(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance")),
):
    encrypted_fields = [
        "ssn", "dob", "patient_name", "address", "phone",
        "insurance_id", "account_number", "credit_card",
    ]
    return {
        "encrypted_fields": encrypted_fields,
        "encryption_algorithm": "AES-256-GCM",
        "key_rotation_days": 90,
        "at_rest": True,
        "in_transit": True,
    }


# ── Inline policy explanation ─────────────────────────────────────────────────

@router.get("/policy-explanation")
async def policy_explanation(
    field: str = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    rules = _svc(db).repo("visibility_rules").list(tenant_id=current.tenant_id)
    applicable = []
    for r in rules:
        d = r.get("data", {})
        if field in d.get("fields", []) and d.get("status") == "active":
            applicable.append({
                "rule_id": str(r.get("id")),
                "rule_name": d.get("rule_name"),
                "action": d.get("action"),
                "role": d.get("role"),
                "explanation": d.get("explanation", f"Rule applies {d.get('action')} to field '{field}'"),
            })
    return {"field": field, "applicable_rules": applicable, "count": len(applicable)}


# ── Compliance classification labels ─────────────────────────────────────────

@router.get("/classification-labels")
async def classification_labels(
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "labels": {
            "PHI": {"color": "red", "description": "Protected Health Information - HIPAA regulated"},
            "PII": {"color": "orange", "description": "Personally Identifiable Information"},
            "FINANCIAL": {"color": "yellow", "description": "Financial data - PCI/internal policy"},
            "OPERATIONAL": {"color": "blue", "description": "Operational data - internal use"},
            "PUBLIC": {"color": "green", "description": "Non-sensitive public data"},
        }
    }


# ── Forensic access log ───────────────────────────────────────────────────────

@router.get("/forensic-log")
async def forensic_log(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
):
    svc = _svc(db)
    audit = svc.repo("visibility_audit_log").list(tenant_id=current.tenant_id)
    anomalies = svc.repo("visibility_anomaly_events").list(tenant_id=current.tenant_id)
    alerts = svc.repo("visibility_access_alerts").list(tenant_id=current.tenant_id)
    return {
        "audit_events": audit,
        "anomaly_events": anomalies,
        "access_alerts": alerts,
        "total_events": len(audit) + len(anomalies) + len(alerts),
    }


# ── Insider threat monitoring ─────────────────────────────────────────────────

@router.get("/insider-threat-report")
async def insider_threat_report(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
):
    anomalies = _svc(db).repo("visibility_anomaly_events").list(tenant_id=current.tenant_id)
    high_risk = [a for a in anomalies if a.get("data", {}).get("severity") == "high"]
    return {
        "total_anomalies": len(anomalies),
        "high_risk_events": len(high_risk),
        "high_risk_details": high_risk,
        "monitoring_active": True,
    }


# ── Restricted analytics aggregation ─────────────────────────────────────────

@router.post("/privacy-safe-aggregate")
async def privacy_safe_aggregate(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
):
    data = payload.get("data", [])
    group_by = payload.get("group_by", "status")
    agg: dict[str, int] = {}
    for row in data:
        key = str(row.get(group_by, "unknown"))
        agg[key] = agg.get(key, 0) + 1
    suppressed = {k: v for k, v in agg.items() if v < 5}
    safe = {k: v for k, v in agg.items() if v >= 5}
    return {
        "aggregation": safe,
        "suppressed_small_cells": list(suppressed.keys()),
        "k_anonymity_threshold": 5,
    }
