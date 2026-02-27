package fusionems

import future.keywords.in

# ── Defaults ─────────────────────────────────────────────────────────────────
default allow = false

# ── Public paths (no auth required) ──────────────────────────────────────────
allow {
    input.path[0] == "healthz"
}

allow {
    input.path[0] == "health"
}

allow {
    input.path[0] == "track"
}

allow {
    input.path[0] == "public"
}

# Webhooks inbound paths are verified by HMAC in application layer
allow {
    input.path[0] == "api"
    input.path[1] == "v1"
    input.path[2] == "webhooks"
}

# ── Authenticated requests ────────────────────────────────────────────────────
allow {
    is_authenticated
    tenant_matches
    role_allows_method
}

# ── Founder role: unrestricted access ────────────────────────────────────────
allow {
    is_authenticated
    input.user.role == "founder"
}

# ── Helpers ───────────────────────────────────────────────────────────────────
is_authenticated {
    input.user.sub != ""
    input.user.tenant_id != ""
}

# Tenant isolation: the user's tenant must match the resource tenant
tenant_matches {
    input.user.tenant_id == input.resource.tenant_id
}

# Allow when no resource tenant is specified (non-tenant-scoped endpoints)
tenant_matches {
    not input.resource.tenant_id
}

# ── Role-based method control ─────────────────────────────────────────────────
role_allows_method {
    input.user.role in {"agency_admin", "supervisor"}
    input.method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
}

role_allows_method {
    input.user.role in {"billing", "billing_admin"}
    input.method in {"GET", "POST", "PUT", "PATCH"}
    billing_path
}

role_allows_method {
    input.user.role == "ems_crew"
    input.method in {"GET", "POST", "PUT", "PATCH"}
    ems_crew_path
}

role_allows_method {
    input.user.role == "patient"
    input.method in {"GET", "POST"}
    patient_path
}

role_allows_method {
    input.user.role == "readonly"
    input.method == "GET"
}

# ── Path sets ─────────────────────────────────────────────────────────────────
billing_path {
    input.path[2] in {"billing", "claims", "payments", "exports", "reports", "ar-aging", "revenue-forecast"}
}

ems_crew_path {
    input.path[2] in {"incidents", "patients", "vitals", "cad", "transportlink", "nemsis", "scheduling", "fleet", "mdt"}
}

patient_path {
    input.path[2] in {"portal", "statements", "auth-rep", "tracking"}
}

# ── Deny rules (explicit blocks regardless of role) ───────────────────────────
# Block cross-tenant data access
deny[msg] {
    is_authenticated
    input.resource.tenant_id != ""
    input.user.tenant_id != input.resource.tenant_id
    input.user.role != "founder"
    msg := sprintf("cross-tenant access denied: user tenant %v != resource tenant %v", [input.user.tenant_id, input.resource.tenant_id])
}

# Block non-founders from founder endpoints
deny[msg] {
    is_authenticated
    input.path[2] == "founder"
    input.user.role != "founder"
    msg := "founder endpoint requires founder role"
}
