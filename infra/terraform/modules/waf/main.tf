################################################################################
# WAF Module – maps from CloudFormation waf.yml
################################################################################

terraform {
  required_version = ">= 1.6"
}

locals {
  webhook_ip_allowlist_enforced = length(var.stripe_webhook_cidrs) > 0 && length(var.telnyx_webhook_cidrs) > 0 && length(var.lob_webhook_cidrs) > 0
}

# ── IP Sets ──────────────────────────────────────────────────────────────────

resource "aws_wafv2_ip_set" "stripe_webhooks" {
  count              = length(var.stripe_webhook_cidrs) > 0 ? 1 : 0
  name               = "${var.project}-${var.environment}-stripe-webhooks"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.stripe_webhook_cidrs

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-stripe-webhooks"
  })
}

resource "aws_wafv2_ip_set" "telnyx_webhooks" {
  count              = length(var.telnyx_webhook_cidrs) > 0 ? 1 : 0
  name               = "${var.project}-${var.environment}-telnyx-webhooks"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.telnyx_webhook_cidrs

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-telnyx-webhooks"
  })
}

resource "aws_wafv2_ip_set" "lob_webhooks" {
  count              = length(var.lob_webhook_cidrs) > 0 ? 1 : 0
  name               = "${var.project}-${var.environment}-lob-webhooks"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.lob_webhook_cidrs

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-lob-webhooks"
  })
}

# ── Web ACL ──────────────────────────────────────────────────────────────────

resource "aws_wafv2_web_acl" "this" {
  name  = "${var.project}-${var.environment}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project}-${var.environment}-waf"
  }

  # ── Priority 1: Allow Stripe webhooks ────────────────────────────────────

  dynamic "rule" {
    for_each = length(var.stripe_webhook_cidrs) > 0 ? [1] : []
    content {
      name     = "AllowStripeWebhooks"
      priority = 1

      action {
        allow {}
      }

      statement {
        and_statement {
          statement {
            ip_set_reference_statement {
              arn = aws_wafv2_ip_set.stripe_webhooks[0].arn
            }
          }
          statement {
            byte_match_statement {
              search_string         = "/api/v1/webhooks/stripe"
              positional_constraint = "STARTS_WITH"

              field_to_match {
                uri_path {}
              }

              text_transformation {
                priority = 0
                type     = "NONE"
              }
            }
          }
        }
      }

      visibility_config {
        sampled_requests_enabled   = true
        cloudwatch_metrics_enabled = true
        metric_name                = "AllowStripeWebhooks"
      }
    }
  }

  # ── Priority 2: Allow Telnyx webhooks ────────────────────────────────────

  dynamic "rule" {
    for_each = length(var.telnyx_webhook_cidrs) > 0 ? [1] : []
    content {
      name     = "AllowTelnyxWebhooks"
      priority = 2

      action {
        allow {}
      }

      statement {
        and_statement {
          statement {
            ip_set_reference_statement {
              arn = aws_wafv2_ip_set.telnyx_webhooks[0].arn
            }
          }
          statement {
            byte_match_statement {
              search_string         = "/api/v1/webhooks/telnyx"
              positional_constraint = "STARTS_WITH"

              field_to_match {
                uri_path {}
              }

              text_transformation {
                priority = 0
                type     = "NONE"
              }
            }
          }
        }
      }

      visibility_config {
        sampled_requests_enabled   = true
        cloudwatch_metrics_enabled = true
        metric_name                = "AllowTelnyxWebhooks"
      }
    }
  }

  dynamic "rule" {
    for_each = length(var.lob_webhook_cidrs) > 0 ? [1] : []
    content {
      name     = "AllowLobWebhooks"
      priority = 3

      action {
        allow {}
      }

      statement {
        and_statement {
          statement {
            ip_set_reference_statement {
              arn = aws_wafv2_ip_set.lob_webhooks[0].arn
            }
          }
          statement {
            byte_match_statement {
              search_string         = "/api/v1/webhooks/lob"
              positional_constraint = "STARTS_WITH"

              field_to_match {
                uri_path {}
              }

              text_transformation {
                priority = 0
                type     = "NONE"
              }
            }
          }
        }
      }

      visibility_config {
        sampled_requests_enabled   = true
        cloudwatch_metrics_enabled = true
        metric_name                = "AllowLobWebhooks"
      }
    }
  }

  # ── Priority 3: Block non-allowlisted webhook traffic ────────────────────

  dynamic "rule" {
    for_each = local.webhook_ip_allowlist_enforced ? [1] : []
    content {
      name     = "BlockNonAllowlistedWebhookTraffic"
      priority = 4

      action {
        block {}
      }

      statement {
        byte_match_statement {
          search_string         = "/api/v1/webhooks/"
          positional_constraint = "STARTS_WITH"

          field_to_match {
            uri_path {}
          }

          text_transformation {
            priority = 0
            type     = "NONE"
          }
        }
      }

      visibility_config {
        sampled_requests_enabled   = true
        cloudwatch_metrics_enabled = true
        metric_name                = "BlockNonAllowlistedWebhookTraffic"
      }
    }
  }

  # ── Priority 10: AWS Managed Rules – Common Rule Set ─────────────────────

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 10

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSet"
    }
  }

  # ── Priority 11: AWS Managed Rules – Known Bad Inputs ────────────────────

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 11

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "KnownBadInputs"
    }
  }

  # ── Priority 12: AWS Managed Rules – SQLi ────────────────────────────────

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 12

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLi"
    }
  }

  # ── Priority 20: Global rate limit ───────────────────────────────────────

  rule {
    name     = "GlobalRateLimit"
    priority = 20

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 1500
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "GlobalRateLimit"
    }
  }

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-waf"
  })
}

# ── WAF Logging ──────────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-${var.project}-${var.environment}"
  retention_in_days = 90

  tags = merge(var.tags, {
    Name = "aws-waf-logs-${var.project}-${var.environment}"
  })
}

resource "aws_wafv2_web_acl_logging_configuration" "this" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.this.arn
}
