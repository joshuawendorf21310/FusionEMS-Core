###############################################################################
# FusionEMS – Environment-specific values (dev)
# NOTE: Do NOT put secrets here. Use TF_VAR_* env vars or a secrets manager.
###############################################################################

environment = "dev"
aws_region  = "us-east-1"

# ─── Networking ──────────────────────────────────────────────────────────────

vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]

# ─── DNS ─────────────────────────────────────────────────────────────────────

root_domain_name = "dev.fusionemsquantum.com"
api_domain_name  = "api.dev.fusionemsquantum.com"
hosted_zone_id   = "Z0858801IZXAHSWCPH85"

# ─── Compute ─────────────────────────────────────────────────────────────────

db_instance_class = "db.t4g.medium"
redis_node_type   = "cache.t4g.small"

# ─── Monitoring ──────────────────────────────────────────────────────────────

alert_email = "alerts+dev@fusionemsquantum.com"
