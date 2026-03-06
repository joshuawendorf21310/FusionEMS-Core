###############################################################################
# FusionEMS – Terraform root configuration (shared across all environments)
###############################################################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# ─── Providers ───────────────────────────────────────────────────────────────

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}

# ─── Data Sources ────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}

# ─── Locals ──────────────────────────────────────────────────────────────────

locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  alb_arn_suffix        = replace(module.ecs_cluster.alb_arn, "/^.*:loadbalancer\\//", "")
  backend_tg_arn_suffix = replace(module.backend_service.target_group_arn, "/^.*:targetgroup\\//", "")
}

# ─── 1. Networking ───────────────────────────────────────────────────────────

module "networking" {
  source = "../../modules/networking"

  environment          = var.environment
  project              = var.project
  region               = var.aws_region
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  acm_certificate_arn  = module.acm.certificate_arn
  tags                 = local.common_tags
}

# ─── 2. IAM ──────────────────────────────────────────────────────────────────

module "iam" {
  source = "../../modules/iam"

  environment = var.environment
  project     = var.project
  region      = var.aws_region
  account_id  = data.aws_caller_identity.current.account_id
  github_org  = var.github_org
  github_repo = var.github_repo

  ecr_repository_arns = [
    "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${var.project}-${var.environment}-*"
  ]
  s3_bucket_arns = [
    module.s3.docs_bucket_arn,
    module.s3.exports_bucket_arn,
    module.s3.proposals_bucket_arn,
    module.s3.audit_bucket_arn,
    module.s3.artifacts_bucket_arn,
  ]
  sqs_queue_arns = module.sqs.all_queue_arns
  sns_topic_arns = [module.observability.alert_topic_arn]
  secrets_arns = [
    module.rds.db_secret_arn,
    module.redis.auth_secret_arn,
    module.ses.graph_email_secret_arn,
  ]
  kms_key_arns = [
    module.rds.kms_key_arn,
    module.s3.kms_key_arn,
  ]
  tags = local.common_tags
}

# ─── 3. ACM ──────────────────────────────────────────────────────────────────

module "acm" {
  source = "../../modules/acm"

  environment      = var.environment
  project          = var.project
  root_domain_name = var.root_domain_name
  api_domain_name  = var.api_domain_name
  hosted_zone_id   = var.hosted_zone_id
  tags             = local.common_tags
}

# ─── 4. S3 ───────────────────────────────────────────────────────────────────

module "s3" {
  source = "../../modules/s3"

  environment = var.environment
  project     = var.project
  tags        = local.common_tags
}

# ─── 5. WAF ──────────────────────────────────────────────────────────────────

module "waf" {
  source = "../../modules/waf"

  environment = var.environment
  project     = var.project
  tags        = local.common_tags
}

# ─── 6. ECS Cluster ─────────────────────────────────────────────────────────

module "ecs_cluster" {
  source = "../../modules/ecs-cluster"

  environment           = var.environment
  project               = var.project
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  private_subnet_ids    = module.networking.private_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
  acm_certificate_arn   = module.acm.certificate_arn
  waf_acl_arn           = module.waf.web_acl_arn
  enable_waf            = true
  tags                  = local.common_tags
}

# ─── 7. RDS ──────────────────────────────────────────────────────────────────

module "rds" {
  source = "../../modules/rds"

  environment           = var.environment
  project               = var.project
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.networking.ecs_security_group_id
  rds_security_group_id = module.networking.rds_security_group_id
  instance_class        = var.db_instance_class
  tags                  = local.common_tags
}

# ─── 8. Redis ────────────────────────────────────────────────────────────────

module "redis" {
  source = "../../modules/redis"

  environment             = var.environment
  project                 = var.project
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  redis_security_group_id = module.networking.redis_security_group_id
  node_type               = var.redis_node_type
  tags                    = local.common_tags
}

# ─── 9. Cognito ──────────────────────────────────────────────────────────────

module "cognito" {
  source = "../../modules/cognito"

  environment   = var.environment
  project       = var.project
  callback_urls = ["https://${var.root_domain_name}/auth/callback"]
  logout_urls   = ["https://${var.root_domain_name}"]
  tags          = local.common_tags
}

# ─── 10. Observability ──────────────────────────────────────────────────────

module "observability" {
  source = "../../modules/observability"

  environment                     = var.environment
  project                         = var.project
  alert_email                     = var.alert_email
  ecs_cluster_name                = module.ecs_cluster.cluster_name
  backend_service_name            = module.backend_service.service_name
  alb_arn_suffix                  = local.alb_arn_suffix
  backend_target_group_arn_suffix = local.backend_tg_arn_suffix
  db_instance_id                  = module.rds.db_instance_id
  redis_cluster_id                = module.redis.replication_group_id
  tags                            = local.common_tags
}

# ─── 11. Edge (CloudFront + Route53) ────────────────────────────────────────

module "edge" {
  source = "../../modules/edge"

  environment                   = var.environment
  project                       = var.project
  root_domain_name              = var.root_domain_name
  api_domain_name               = var.api_domain_name
  hosted_zone_id                = var.hosted_zone_id
  acm_certificate_arn_us_east_1 = module.acm.certificate_arn
  alb_dns_name                  = module.ecs_cluster.alb_dns_name
  tags                          = local.common_tags

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
}

# ─── 12. SES ─────────────────────────────────────────────────────────────────

module "ses" {
  source = "../../modules/ses"

  environment         = var.environment
  project             = var.project
  graph_tenant_id     = var.graph_tenant_id
  graph_client_id     = var.graph_client_id
  graph_client_secret = var.graph_client_secret
  graph_founder_email = var.graph_founder_email
  tags                = local.common_tags
}

# ─── 12b. SQS Queues ────────────────────────────────────────────────────────

module "sqs" {
  source = "../../modules/sqs"

  environment = var.environment
  project     = var.project
  tags        = local.common_tags

  queues = {
    neris-pack-import  = {}
    neris-pack-compile = {}
    neris-export       = {}
  }
}

# ─── 13. Backend Service ────────────────────────────────────────────────────

module "backend_service" {
  source = "../../modules/ecs-service"

  environment            = var.environment
  project                = var.project
  service_name           = "backend"
  cluster_id             = module.ecs_cluster.cluster_id
  cluster_name           = module.ecs_cluster.cluster_name
  vpc_id                 = module.networking.vpc_id
  private_subnet_ids     = module.networking.private_subnet_ids
  security_group_ids     = [module.networking.ecs_security_group_id]
  execution_role_arn     = module.iam.ecs_task_execution_role_arn
  task_role_arn          = module.iam.ecs_task_role_arn
  container_image        = "${module.ecs_cluster.backend_ecr_repository_url}:${var.backend_image_tag}"
  container_port         = 8000
  cpu                    = 1024
  memory                 = 2048
  alb_listener_arn       = module.ecs_cluster.alb_listener_arn
  path_pattern           = ["/api/*"]
  listener_rule_priority = 10
  log_group_name         = module.ecs_cluster.log_group_name
  tags                   = local.common_tags

  environment_variables = [
    { name = "ENVIRONMENT", value = var.environment },
    { name = "AWS_DEFAULT_REGION", value = var.aws_region },
    { name = "COGNITO_USER_POOL_ID", value = module.cognito.user_pool_id },
    { name = "COGNITO_CLIENT_ID", value = module.cognito.user_pool_client_id },
    { name = "S3_DOCS_BUCKET", value = module.s3.docs_bucket_name },
    { name = "S3_EXPORTS_BUCKET", value = module.s3.exports_bucket_name },
    { name = "S3_PROPOSALS_BUCKET", value = module.s3.proposals_bucket_name },
  ]

  secrets = [
    { name = "DATABASE_URL", valueFrom = module.rds.db_secret_arn },
    { name = "REDIS_URL", valueFrom = module.redis.auth_secret_arn },
  ]
}

# ─── 14. Frontend Service ───────────────────────────────────────────────────

module "frontend_service" {
  source = "../../modules/ecs-service"

  environment            = var.environment
  project                = var.project
  service_name           = "frontend"
  cluster_id             = module.ecs_cluster.cluster_id
  cluster_name           = module.ecs_cluster.cluster_name
  vpc_id                 = module.networking.vpc_id
  private_subnet_ids     = module.networking.private_subnet_ids
  security_group_ids     = [module.networking.ecs_security_group_id]
  execution_role_arn     = module.iam.ecs_task_execution_role_arn
  task_role_arn          = module.iam.ecs_task_role_arn
  container_image        = "${module.ecs_cluster.frontend_ecr_repository_url}:${var.frontend_image_tag}"
  container_port         = 3000
  cpu                    = 512
  memory                 = 1024
  alb_listener_arn       = module.ecs_cluster.alb_listener_arn
  path_pattern           = ["/*"]
  listener_rule_priority = 100
  log_group_name         = module.ecs_cluster.log_group_name
  health_check_path      = "/healthz"
  tags                   = local.common_tags

  container_healthcheck_command = [
    "CMD-SHELL",
    "node -e \"require('http').get('http://127.0.0.1:3000/healthz', (res) => process.exit(res.statusCode >= 200 && res.statusCode < 300 ? 0 : 1)).on('error', () => process.exit(1))\""
  ]

  environment_variables = [
    { name = "ENVIRONMENT", value = var.environment },
    { name = "NEXT_PUBLIC_API_BASE", value = "https://${var.api_domain_name}" },
    { name = "NEXT_PUBLIC_BACKEND_URL", value = "https://${var.api_domain_name}" },
    { name = "BACKEND_URL", value = "https://${var.api_domain_name}" },
    { name = "NEXT_PUBLIC_WS_URL", value = "wss://${var.api_domain_name}/api/v1/realtime/ws" },
    { name = "NEXT_PUBLIC_API_URL", value = "https://${var.api_domain_name}" },
    { name = "NEXT_PUBLIC_COGNITO_USER_POOL_ID", value = module.cognito.user_pool_id },
    { name = "NEXT_PUBLIC_COGNITO_CLIENT_ID", value = module.cognito.user_pool_client_id },
  ]

  secrets = []
}
