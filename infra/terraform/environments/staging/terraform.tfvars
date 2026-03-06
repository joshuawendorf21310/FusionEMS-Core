###############################################################################
# FusionEMS – Environment-specific values (staging)
# NOTE: Do NOT put secrets here. Use TF_VAR_* env vars or a secrets manager.
###############################################################################

environment = "staging"
aws_region  = "us-east-1"

# ─── Networking ──────────────────────────────────────────────────────────────

vpc_cidr           = "10.1.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
private_subnet_cidrs = ["10.1.11.0/24", "10.1.12.0/24", "10.1.13.0/24"]

# ─── DNS ─────────────────────────────────────────────────────────────────────

root_domain_name = "staging.fusionemsquantum.com"
api_domain_name  = "api.staging.fusionemsquantum.com"
hosted_zone_id   = "Z0858801IZXAHSWCPH85"

# ─── Compute ─────────────────────────────────────────────────────────────────

db_instance_class = "db.t4g.large"
redis_node_type   = "cache.t4g.medium"

# ─── Monitoring ──────────────────────────────────────────────────────────────

alert_email = "alerts+staging@fusionemsquantum.com"
