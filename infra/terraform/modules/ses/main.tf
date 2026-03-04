###############################################################################
# FusionEMS SES Module
# Microsoft Graph Email credentials and IAM access policy
###############################################################################

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
}

data "aws_caller_identity" "current" {}

# =============================================================================
# KMS
# =============================================================================

data "aws_iam_policy_document" "ses_kms" {
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

resource "aws_kms_key" "ses" {
  description         = "${local.name_prefix}-ses"
  enable_key_rotation = true
  policy              = data.aws_iam_policy_document.ses_kms.json
  tags                = local.common_tags
}

# =============================================================================
# Secrets Manager
# =============================================================================

resource "aws_secretsmanager_secret" "graph_email" {
  name        = "${local.name_prefix}-graph-email"
  description = "Microsoft Graph credentials for Founder Dashboard email"
  kms_key_id  = aws_kms_key.ses.arn

  tags = local.common_tags
}

# NOTE: Do not manage secret values with Terraform (no aws_secretsmanager_secret_version)

# =============================================================================
# IAM Policy
# =============================================================================

data "aws_iam_policy_document" "graph_email_access" {
  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.graph_email.arn]
  }
}

resource "aws_iam_policy" "graph_email_access" {
  name        = "${local.name_prefix}-GraphEmailAccess"
  description = "Allow read access to the Microsoft Graph email secret"
  policy      = data.aws_iam_policy_document.graph_email_access.json

  tags = local.common_tags
}
