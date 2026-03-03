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

# =============================================================================
# Secrets Manager
# =============================================================================

resource "aws_secretsmanager_secret" "graph_email" {
  name        = "${local.name_prefix}-graph-email"
  description = "Microsoft Graph credentials for Founder Dashboard email"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "graph_email" {
  secret_id = aws_secretsmanager_secret.graph_email.id
  secret_string = jsonencode({
    tenant_id     = var.graph_tenant_id
    client_id     = var.graph_client_id
    client_secret = var.graph_client_secret
    founder_email = var.graph_founder_email
  })
}

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
