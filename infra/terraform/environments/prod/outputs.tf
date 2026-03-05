###############################################################################
# FusionEMS – Outputs (shared across all environments)
###############################################################################

# ─── Networking ──────────────────────────────────────────────────────────────

output "vpc_id" {
  description = "VPC identifier"
  value       = module.networking.vpc_id
}

# ─── Load Balancer ───────────────────────────────────────────────────────────

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.ecs_cluster.alb_dns_name
}

# ─── CDN ─────────────────────────────────────────────────────────────────────

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = module.edge.cloudfront_domain_name
}

# ─── Database ────────────────────────────────────────────────────────────────

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = module.rds.db_endpoint
  sensitive   = true
}

# ─── Cache ───────────────────────────────────────────────────────────────────

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = module.redis.primary_endpoint
  sensitive   = true
}

# ─── NERIS (SQS) ────────────────────────────────────────────────────────────

output "neris_pack_import_queue_url" {
  description = "NERIS pack import SQS queue URL"
  value       = module.sqs.queue_urls["neris-pack-import"]
}

output "neris_pack_compile_queue_url" {
  description = "NERIS pack compile SQS queue URL"
  value       = module.sqs.queue_urls["neris-pack-compile"]
}

output "neris_export_queue_url" {
  description = "NERIS export SQS queue URL"
  value       = module.sqs.queue_urls["neris-export"]
}

# ─── Container Registries ───────────────────────────────────────────────────

output "backend_ecr_repository_url" {
  description = "ECR repository URL for the backend service"
  value       = module.ecs_cluster.backend_ecr_repository_url
}

output "frontend_ecr_repository_url" {
  description = "ECR repository URL for the frontend service"
  value       = module.ecs_cluster.frontend_ecr_repository_url
}

# ─── Authentication ─────────────────────────────────────────────────────────

output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito user pool client ID"
  value       = module.cognito.user_pool_client_id
}

output "cognito_user_pool_endpoint" {
  description = "Cognito user pool endpoint"
  value       = module.cognito.user_pool_endpoint
}
