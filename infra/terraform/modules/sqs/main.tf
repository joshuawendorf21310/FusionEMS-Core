################################################################################
# SQS Module – Reusable queues with dead-letter queues
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
}

# ─── Dead-Letter Queues ──────────────────────────────────────────────────────

resource "aws_sqs_queue" "dlq" {
  for_each = var.queues

  name                       = "${local.name_prefix}-${each.key}-dlq"
  receive_wait_time_seconds  = each.value.receive_wait_time_seconds
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  sqs_managed_sse_enabled    = true

  tags = merge(local.common_tags, {
    Owner     = "FusionEMS"
    Component = each.key
    DataClass = "internal"
  })
}

# ─── Main Queues ─────────────────────────────────────────────────────────────

resource "aws_sqs_queue" "main" {
  for_each = var.queues

  name                       = "${local.name_prefix}-${each.key}"
  receive_wait_time_seconds  = each.value.receive_wait_time_seconds
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = each.value.max_receive_count
  })

  tags = merge(local.common_tags, {
    Owner     = "FusionEMS"
    Component = each.key
    DataClass = "internal"
  })
}
