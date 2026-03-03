################################################################################
# S3 Module – maps from CloudFormation s3.yml
################################################################################

terraform {
  required_version = ">= 1.6"
}

data "aws_caller_identity" "current" {}

# ── KMS key shared across buckets ────────────────────────────────────────────

data "aws_iam_policy_document" "s3_kms" {
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

resource "aws_kms_key" "s3" {
  description             = "${var.project}-${var.environment} S3 encryption key"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy                  = data.aws_iam_policy_document.s3_kms.json
  tags                    = var.tags
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.project}-${var.environment}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# ── Bucket definitions ───────────────────────────────────────────────────────

locals {
  buckets = {
    docs = {
      suffix          = "docs"
      description     = "Document storage"
      glacier_days    = 90
      expiration_days = 730
      expire          = true
    }
    exports = {
      suffix          = "exports"
      description     = "Export files"
      glacier_days    = 90
      expiration_days = 730
      expire          = true
    }
    proposals = {
      suffix          = "proposals"
      description     = "Proposals"
      glacier_days    = 90
      expiration_days = 730
      expire          = true
    }
    audit = {
      suffix          = "audit"
      description     = "Audit logs"
      glacier_days    = 365
      expiration_days = 0
      expire          = false
    }
    artifacts = {
      suffix          = "artifacts"
      description     = "CFN/deployment artifacts"
      glacier_days    = 90
      expiration_days = 90
      expire          = true
    }
  }
}

# ── S3 buckets ───────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "this" {
  for_each = local.buckets

  bucket        = "${var.project}-${var.environment}-${each.value.suffix}"
  force_destroy = false

  tags = merge(var.tags, {
    Description = each.value.description
  })
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.this[each.key].arn,
          "${aws_s3_bucket.this[each.key].arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# ── Lifecycle rules ──────────────────────────────────────────────────────────

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = local.buckets

  bucket = aws_s3_bucket.this[each.key].id

  rule {
    id     = "AbortIncompleteMultipartUpload"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "IntelligentTiering"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }
  }

  rule {
    id     = "GlacierTransition"
    status = "Enabled"

    transition {
      days          = each.value.glacier_days
      storage_class = "GLACIER"
    }
  }

  dynamic "rule" {
    for_each = each.value.expire ? [1] : []
    content {
      id     = "Expiration"
      status = "Enabled"

      expiration {
        days = each.value.expiration_days
      }
    }
  }
}
