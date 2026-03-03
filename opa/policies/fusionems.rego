package fusionems

import rego.v1

# =============================================================================
# DEFAULTS
# =============================================================================

default allow = false
default deny := set()

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

allow if {
    path0 in {"healthz", "health", "track", "public"}
}

# Webhooks are validated at application layer (HMAC)
allow if {
    _is_webhook_path
}

# =============================================================================
# AUTHENTICATED ACCESS
# =============================================================================

allow if {
    is_authenticated
    not deny[_]
    founder_override
}

allow if {
    is_authenticated
    not deny[_]
    tenant_matches
    role_allows_method
}

# =============================================================================
# FOUNDER OVERRIDE
# =============================================================================

founder_override if {
    input.user.role == "founder"
}

# =============================================================================
# AUTH HELPERS
# =============================================================================

is_authenticated if {
    input.user.sub != ""
    input.user.tenant_id != ""
}

# =============================================================================
# TENANT ISOLATION
# =============================================================================

tenant_matches if {
    not input.resource.tenant_id
}

tenant_matches if {
    input.resource.tenant_id != ""
    input.user.tenant_id == input.resource.tenant_id
}

# =============================================================================
# ROLE-BASED METHOD CONTROL
# =============================================================================

role_allows_method if {
    input.user.role in {"agency_admin", "supervisor"}
    method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
}

role_allows_method if {
    input.user.role in {"billing", "billing_admin"}
    method in {"GET", "POST", "PUT", "PATCH"}
    billing_path
}

role_allows_method if {
    input.user.role == "ems_crew"
    method in {"GET", "POST", "PUT", "PATCH"}
    ems_crew_path
}

role_allows_method if {
    input.user.role == "patient"
    method in {"GET", "POST"}
    patient_path
}

role_allows_method if {
    input.user.role == "readonly"
    method == "GET"
}

# Internal system services (queues, cron, webhooks, etc.)
role_allows_method if {
    input.user.role == "system"
}

# =============================================================================
# PATH SCOPES
# =============================================================================

billing_path if {
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

ems_crew_path if {
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

patient_path if {
    path2 in {
        "portal",
        "statements",
        "auth-rep",
        "tracking"
    }
}

# =============================================================================
# INTERNAL HELPERS
# =============================================================================

_is_webhook_path if {
    path0 == "api"
    path1 == "v1"
    path2 == "webhooks"
}

# =============================================================================
# EXPLICIT DENY RULES (ALWAYS TAKE PRECEDENCE)
# =============================================================================

# Cross-tenant access block
deny contains msg if {
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
deny contains msg if {
    is_authenticated
    path2 == "founder"
    input.user.role != "founder"
    msg := "founder endpoint requires founder role"
}

# Block write attempts from readonly role
deny contains msg if {
    input.user.role == "readonly"
    method != "GET"
    msg := "readonly role cannot modify resources"
}

# Prevent unauthenticated access to protected routes
deny contains msg if {
    not is_authenticated
    not path0 in {"healthz", "health", "track", "public"}
    not _is_webhook_path
    msg := "authentication required"
}
