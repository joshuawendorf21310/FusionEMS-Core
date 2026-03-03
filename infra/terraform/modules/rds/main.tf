###############################################################################
# FusionEMS RDS Module
# PostgreSQL database with encryption, secrets management, and prod hardening
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

data "aws_iam_policy_document" "rds_kms" {
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

resource "aws_kms_key" "rds" {
  description         = "${local.name_prefix}-rds"
  enable_key_rotation = true
  policy              = data.aws_iam_policy_document.rds_kms.json
  tags                = local.common_tags
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.project}-${var.environment}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# =============================================================================
# Networking
# =============================================================================

resource "aws_db_subnet_group" "this" {
  name       = "${local.name_prefix}-rds"
  subnet_ids = var.private_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds"
  })
}

# =============================================================================
# Secrets
# =============================================================================

resource "random_password" "master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}|:?"
}

resource "aws_secretsmanager_secret" "db" {
  name       = "${var.project}/${var.environment}/DB"
  kms_key_id = aws_kms_key.rds.arn
  tags       = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.master.result
    dbname   = var.db_name
  })
}

# =============================================================================
# Enhanced Monitoring IAM Role
# =============================================================================

data "aws_iam_policy_document" "rds_monitoring_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "rds_monitoring" {
  name               = "${local.name_prefix}-rds-monitoring"
  assume_role_policy = data.aws_iam_policy_document.rds_monitoring_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# =============================================================================
# Parameter Group (query logging)
# =============================================================================

resource "aws_db_parameter_group" "this" {
  name   = "${local.name_prefix}-postgres16"
  family = "postgres16"

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "250"
  }

  tags = local.common_tags
}

# =============================================================================
# RDS Instance
# =============================================================================

resource "aws_db_instance" "this" {
  identifier = "${local.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = "16.6"

  instance_class    = var.instance_class
  allocated_storage = 200
  storage_type      = "gp3"
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  db_name  = var.db_name
  username = var.db_username
  password = random_password.master.result

  multi_az            = local.is_prod
  publicly_accessible = false

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.rds_security_group_id]
  parameter_group_name   = aws_db_parameter_group.this.name

  backup_retention_period   = 14
  deletion_protection       = local.is_prod
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name_prefix}-postgres-final"

  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn

  iam_database_authentication_enabled = true
  auto_minor_version_upgrade          = true

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  apply_immediately = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
  })

  lifecycle {
    prevent_destroy = true
  }
}
