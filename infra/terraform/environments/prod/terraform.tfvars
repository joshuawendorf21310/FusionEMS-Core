###############################################################################
# FusionEMS – Environment-specific values (prod)
# NOTE: Do NOT put secrets here. Use TF_VAR_* env vars or a secrets manager.
###############################################################################

environment = "prod"
aws_region  = "us-east-1"

# ─── Networking ──────────────────────────────────────────────────────────────

vpc_cidr           = "10.2.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

public_subnet_cidrs  = ["10.2.1.0/24", "10.2.2.0/24", "10.2.3.0/24"]
private_subnet_cidrs = ["10.2.11.0/24", "10.2.12.0/24", "10.2.13.0/24"]

# ─── DNS ─────────────────────────────────────────────────────────────────────

root_domain_name = "fusionemsquantum.com"
api_domain_name  = "api.fusionemsquantum.com"
hosted_zone_id   = "Z0858801IZXAHSWCPH85"

# ─── Compute ─────────────────────────────────────────────────────────────────

db_instance_class = "db.t4g.large"
redis_node_type   = "cache.t4g.medium"

# Application image tags (ECR)
# NOTE: Use immutable tags (not "latest") so ECS deployments always pick up the intended build.
backend_image_tag  = "hc-20260305015136-eb18a434"
frontend_image_tag = "hc-20260305012629-eb18a434"

# ─── Monitoring ──────────────────────────────────────────────────────────────

alert_email = "alerts@fusionemsquantum.com"

# ─── CI / CD (GitHub Actions OIDC) ──────────────────────────────────────────

# IMPORTANT: these must match the GitHub repo that runs the workflows.
github_org  = "FusionEMS-Quantum"
github_repo = "FusionEMS-Core"

# Match the role assumed by workflows (.github/workflows/terraform*.yml)
github_actions_role_name = "FusionEMS-GHA-TerraformProd"

# Restrict OIDC to main branch pushes and PR workflows only.
github_allowed_subjects = [
  "repo:FusionEMS-Quantum/FusionEMS-Core:ref:refs/heads/main",
  "repo:FusionEMS-Quantum/FusionEMS-Core:pull_request",
]
