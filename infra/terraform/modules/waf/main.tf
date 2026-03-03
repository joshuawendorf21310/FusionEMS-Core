################################################################################
# WAF Module – maps from CloudFormation waf.yml
################################################################################

terraform {
  required_version = ">= 1.6"
}

# ── IP Sets ──────────────────────────────────────────────────────────────────

resource "aws_wafv2_ip_set" "stripe_webhooks" {
  name               = "${var.project}-${var.environment}-stripe-webhooks"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.stripe_webhook_cidrs

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-stripe-webhooks"
  })
}

resource "aws_wafv2_ip_set" "telnyx_webhooks" {
  name               = "${var.project}-${var.environment}-telnyx-webhooks"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.telnyx_webhook_cidrs

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-telnyx-webhooks"
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

  rule {
    name     = "AllowStripeWebhooks"
    priority = 1

    action {
      allow {}
    }

    statement {
      and_statement {
        statement {
          ip_set_reference_statement {
            arn = aws_wafv2_ip_set.stripe_webhooks.arn
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

  # ── Priority 2: Allow Telnyx webhooks ────────────────────────────────────

  rule {
    name     = "AllowTelnyxWebhooks"
    priority = 2

    action {
      allow {}
    }

    statement {
      and_statement {
        statement {
          ip_set_reference_statement {
            arn = aws_wafv2_ip_set.telnyx_webhooks.arn
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

  # ── Priority 3: Block non-allowlisted webhook traffic ────────────────────

  rule {
    name     = "BlockNonAllowlistedWebhookTraffic"
    priority = 3

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
