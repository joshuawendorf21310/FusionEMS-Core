###############################################################################
# FusionEMS – Environment-specific values (dr)
# NOTE: Do NOT put secrets here. Use TF_VAR_* env vars or a secrets manager.
###############################################################################

environment = "dr"
aws_region  = "us-west-2"

# ─── Networking ──────────────────────────────────────────────────────────────

vpc_cidr           = "10.3.0.0/16"
availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]

public_subnet_cidrs  = ["10.3.1.0/24", "10.3.2.0/24", "10.3.3.0/24"]
private_subnet_cidrs = ["10.3.11.0/24", "10.3.12.0/24", "10.3.13.0/24"]

# ─── DNS ─────────────────────────────────────────────────────────────────────

root_domain_name = "dr.fusionemsquantum.com"
api_domain_name  = "api.dr.fusionemsquantum.com"
hosted_zone_id   = "Z0858801IZXAHSWCPH85"

# ─── Compute ─────────────────────────────────────────────────────────────────

db_instance_class = "db.t4g.large"
redis_node_type   = "cache.t4g.medium"

# ─── Monitoring ──────────────────────────────────────────────────────────────

alert_email = "alerts+dr@fusionemsquantum.com"
