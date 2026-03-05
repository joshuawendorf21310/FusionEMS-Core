################################################################################
# ACM Module – maps from CloudFormation acm.yml
################################################################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ── ACM certificate ─────────────────────────────────────────────────────────

resource "aws_acm_certificate" "this" {
  domain_name               = var.root_domain_name
  subject_alternative_names = ["www.${var.root_domain_name}", var.api_domain_name]
  validation_method         = "DNS"

  tags = merge(var.tags, {
    Name = "${var.project}-${var.environment}-cert"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ── DNS validation records ──────────────────────────────────────────────────

resource "aws_route53_record" "validation" {
  for_each = {
    for dvo in aws_acm_certificate.this.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id         = var.hosted_zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 300
  records         = [each.value.record]
  allow_overwrite = true
}

# ── Wait for validation ─────────────────────────────────────────────────────

resource "aws_acm_certificate_validation" "this" {
  certificate_arn         = aws_acm_certificate.this.arn
  validation_record_fqdns = [for r in aws_route53_record.validation : r.fqdn]
}
