###############################################################################
# FusionEMS Redis Module
# ElastiCache Redis with encryption, auth, and prod high-availability
###############################################################################

terraform {
  required_version = ">= 1.6"
}

locals {
  name_prefix = "${var.project}-${var.environment}"
  is_prod     = var.environment == "prod"

  common_tags = merge(var.tags, {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

data "aws_caller_identity" "current" {}

# =============================================================================
# KMS
# =============================================================================

data "aws_iam_policy_document" "redis_kms" {
  statement {
    sid    = "EnableRootAccountAccess"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }
}

resource "aws_kms_key" "redis" {
  description         = "${local.name_prefix}-redis"
  enable_key_rotation = true
  policy              = data.aws_iam_policy_document.redis_kms.json
  tags                = local.common_tags
}

resource "aws_kms_alias" "redis" {
  name          = "alias/${var.project}-${var.environment}-redis"
  target_key_id = aws_kms_key.redis.key_id
}

# =============================================================================
# Networking
# =============================================================================

resource "aws_elasticache_subnet_group" "this" {
  name       = "${local.name_prefix}-redis"
  subnet_ids = var.private_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
  })
}

# =============================================================================
# Secrets
# =============================================================================

resource "random_password" "auth_token" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}|:?"
}

resource "aws_secretsmanager_secret" "redis" {
  name       = "${var.project}/${var.environment}/Redis"
  kms_key_id = aws_kms_key.redis.arn
  tags       = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id     = aws_secretsmanager_secret.redis.id
  secret_string = random_password.auth_token.result
}

# =============================================================================
# ElastiCache Replication Group
# =============================================================================

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${local.name_prefix}-redis"
  description          = "${local.name_prefix} Enterprise Redis"

  engine         = "redis"
  engine_version = "7.0"
  node_type      = var.node_type

  num_cache_clusters         = local.is_prod ? 2 : 1
  automatic_failover_enabled = local.is_prod
  multi_az_enabled           = local.is_prod

  at_rest_encryption_enabled = true
  kms_key_id                 = aws_kms_key.redis.arn
  transit_encryption_enabled = true
  auth_token                 = random_password.auth_token.result

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [var.redis_security_group_id]

  snapshot_retention_limit = 7
  parameter_group_name     = "default.redis7"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
  })
}
