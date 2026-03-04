################################################################################
# Cognito Module – maps from CloudFormation cognito.yml
################################################################################

terraform {
  required_version = ">= 1.6"
}

data "aws_region" "current" {}

# ── User Pool ────────────────────────────────────────────────────────────────

resource "aws_cognito_user_pool" "this" {
  name = "${var.project}-${var.environment}-userpool"

  lifecycle {
    ignore_changes = [schema]
  }

  username_configuration {
    case_sensitive = false
  }

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  mfa_configuration = var.environment == "prod" ? "ON" : "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  user_pool_add_ons {
    advanced_security_mode = var.environment == "prod" ? "ENFORCED" : "OFF"
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  schema {
    name                = "name"
    attribute_data_type = "String"
    required            = false
    mutable             = true
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  deletion_protection = var.environment == "prod" ? "ACTIVE" : "INACTIVE"

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-userpool"
  })
}

# ── User Pool Client ────────────────────────────────────────────────────────

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.project}-${var.environment}-appclient"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret               = false
  prevent_user_existence_errors = "ENABLED"

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  supported_identity_providers = ["COGNITO"]

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

# ── User Pool Domain ────────────────────────────────────────────────────────

resource "aws_cognito_user_pool_domain" "this" {
  domain       = "${var.project}-${var.environment}-${data.aws_region.current.name}"
  user_pool_id = aws_cognito_user_pool.this.id
}
