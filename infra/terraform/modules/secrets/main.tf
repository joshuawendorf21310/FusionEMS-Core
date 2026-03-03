################################################################################
# Secrets Module - Vendor-scoped Secrets Manager entries
################################################################################

terraform {
  required_version = ">= 1.6"
}

locals {
  name_prefix = "${var.project}-${var.environment}"

  common_tags = merge(var.tags, {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  })

  vendor_secrets = {
    stripe = {
      description = "Stripe API keys and webhook secrets"
      keys        = ["secret_key", "publishable_key", "webhook_secret"]
    }
    telnyx = {
      description = "Telnyx API keys and configuration"
      keys        = ["api_key", "public_key", "webhook_tolerance_seconds"]
    }
    lob = {
      description = "Lob API keys for mail fulfillment"
      keys        = ["api_key", "webhook_secret"]
    }
    openai = {
      description = "OpenAI API keys for AI services"
      keys        = ["api_key", "org_id"]
    }
    officeally = {
      description = "Office Ally SFTP and EDI credentials"
      keys        = ["sftp_host", "sftp_port", "sftp_username", "sftp_password", "sftp_remote_dir"]
    }
  }
}

resource "aws_kms_key" "secrets" {
  description             = "${local.name_prefix} secrets encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = local.common_tags
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${local.name_prefix}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_secretsmanager_secret" "vendor" {
  for_each = local.vendor_secrets

  name        = "${local.name_prefix}/vendors/${each.key}"
  description = each.value.description
  kms_key_id  = aws_kms_key.secrets.arn

  tags = merge(local.common_tags, {
    Vendor = each.key
    Scope  = "vendor"
  })
}

resource "aws_secretsmanager_secret" "app" {
  name        = "${local.name_prefix}/app/config"
  description = "Application-level configuration secrets"
  kms_key_id  = aws_kms_key.secrets.arn

  tags = merge(local.common_tags, {
    Scope = "application"
  })
}

resource "aws_secretsmanager_secret" "founder" {
  name        = "${local.name_prefix}/founder/bootstrap"
  description = "Founder bootstrap credentials (break-glass)"
  kms_key_id  = aws_kms_key.secrets.arn

  tags = merge(local.common_tags, {
    Scope    = "founder"
    Security = "break-glass"
  })
}
