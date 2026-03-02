package fusionems

import future.keywords.in

# =============================================================================
# DEFAULTS
# =============================================================================

default allow = false
default deny = []

# Normalize
method := upper(input.method)

# Safe path helpers
path_len := count(input.path)

path0 := input.path[0] if path_len > 0
path1 := input.path[1] if path_len > 1
path2 := input.path[2] if path_len > 2

# =============================================================================
# PUBLIC (NO AUTH REQUIRED)
# =============================================================================

allow {
    path0 in {"healthz", "health", "track", "public"}
}

# Webhooks are validated at application layer (HMAC)
allow {
    path0 == "api"
    path1 == "v1"
    path2 == "webhooks"
}

# =============================================================================
# AUTHENTICATED ACCESS
# =============================================================================

allow {
    is_authenticated
    not deny[_]
    founder_override
}

allow {
    is_authenticated
    not deny[_]
    tenant_matches
    role_allows_method
}

# =============================================================================
# FOUNDER OVERRIDE
# =============================================================================

founder_override {
    input.user.role == "founder"
}

# =============================================================================
# AUTH HELPERS
# =============================================================================

is_authenticated {
    input.user.sub != ""
    input.user.tenant_id != ""
}

# =============================================================================
# TENANT ISOLATION
# =============================================================================

tenant_matches {
    not input.resource.tenant_id
}

tenant_matches {
    input.resource.tenant_id != ""
    input.user.tenant_id == input.resource.tenant_id
}

# =============================================================================
# ROLE-BASED METHOD CONTROL
# =============================================================================

role_allows_method {
    input.user.role in {"agency_admin", "supervisor"}
    method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
}

role_allows_method {
    input.user.role in {"billing", "billing_admin"}
    method in {"GET", "POST", "PUT", "PATCH"}
    billing_path
}

role_allows_method {
    input.user.role == "ems_crew"
    method in {"GET", "POST", "PUT", "PATCH"}
    ems_crew_path
}

role_allows_method {
    input.user.role == "patient"
    method in {"GET", "POST"}
    patient_path
}

role_allows_method {
    input.user.role == "readonly"
    method == "GET"
}

# Internal system services (queues, cron, webhooks, etc.)
role_allows_method {
    input.user.role == "system"
}

# =============================================================================
# PATH SCOPES
# =============================================================================

billing_path {
    path2 in {
        "billing",
        "claims",
        "payments",
        "exports",
        "reports",
        "ar-aging",
        "revenue-forecast"
    }
}

ems_crew_path {
    path2 in {
        "incidents",
        "patients",
        "vitals",
        "cad",
        "transportlink",
        "nemsis",
        "scheduling",
        "fleet",
        "mdt"
    }
}

patient_path {
    path2 in {
        "portal",
        "statements",
        "auth-rep",
        "tracking"
    }
}

# =============================================================================
# EXPLICIT DENY RULES (ALWAYS TAKE PRECEDENCE)
# =============================================================================

# Cross-tenant access block
deny[msg] {
    is_authenticated
    input.resource.tenant_id != ""
    input.user.tenant_id != input.resource.tenant_id
    input.user.role != "founder"
    msg := sprintf(
        "cross-tenant access denied (user=%v resource=%v)",
        [input.user.tenant_id, input.resource.tenant_id]
    )
}

# Founder endpoints restricted
deny[msg] {
    is_authenticated
    path2 == "founder"
    input.user.role != "founder"
    msg := "founder endpoint requires founder role"
}

# Block write attempts from readonly role
deny[msg] {
    input.user.role == "readonly"
    method != "GET"
    msg := "readonly role cannot modify resources"
}

# Prevent unauthenticated access to protected routes
deny[msg] {
    not is_authenticated
    not path0 in {"healthz", "health", "track", "public"}
    not (path0 == "api" and path1 == "v1" and path2 == "webhooks")
    msg := "authentication required"
}
