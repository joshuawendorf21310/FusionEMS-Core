############################################################
# IAM Module – FusionEMS Sovereign-Grade EMS Platform
############################################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# ── Locals ───────────────────────────────────────────────

locals {
  name_prefix = "${var.project}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags,
  )

  # CloudWatch log group ARN prefix scoped to project.
  # IMPORTANT: log group names are /ecs/<name_prefix> (no trailing dash), and ECS log streams are:
  #   arn:aws:logs:<region>:<acct>:log-group:/ecs/<name_prefix>:log-stream:<container>/<container>/<task-id>
  log_group_arn_prefix = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/ecs/${local.name_prefix}"

  # Terraform remote state backend naming (must match environments/*/backend.tf)
  terraform_state_bucket_name = "${var.project}-terraform-state-${var.environment}"
  terraform_lock_table_name   = "${var.project}-terraform-locks"

  # DynamoDB table ARN pattern scoped to project
  dynamodb_table_arn = "arn:aws:dynamodb:${var.region}:${var.account_id}:table/${local.name_prefix}-*"

  # S3 object ARNs – bucket + bucket/*
  s3_resource_arns = flatten([
    for arn in var.s3_bucket_arns : [arn, "${arn}/*"]
  ])

  github_oidc_url = "https://token.actions.githubusercontent.com"
}

###########################################################
# 1. ECS Task Execution Role
#    – Used by ECS agent to pull images and write logs
###########################################################

data "aws_iam_policy_document" "ecs_task_execution_assume" {
  statement {
    sid     = "ECSTaskExecutionAssume"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${local.name_prefix}-ecs-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume.json
  tags               = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-task-execution" })
}

# ECR pull permissions – scoped to provided repository ARNs

data "aws_iam_policy_document" "ecs_exec_ecr" {
  statement {
    sid    = "ECRGetAuth"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECRPullImages"
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = var.ecr_repository_arns
  }
}

resource "aws_iam_role_policy" "ecs_exec_ecr" {
  name   = "${local.name_prefix}-ecs-exec-ecr"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_exec_ecr.json
}

# CloudWatch Logs permissions – scoped to project log groups

data "aws_iam_policy_document" "ecs_exec_logs" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = [
      # Exact project log group (/ecs/<name_prefix>)
      local.log_group_arn_prefix,
      "${local.log_group_arn_prefix}:log-stream:*",

      # Also allow any future suffixed log groups (/ecs/<name_prefix>-*)
      "${local.log_group_arn_prefix}-*",
      "${local.log_group_arn_prefix}-*:log-stream:*",
    ]
  }
}

resource "aws_iam_role_policy" "ecs_exec_logs" {
  name   = "${local.name_prefix}-ecs-exec-logs"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_exec_logs.json
}

# Secrets Manager read – allows execution role to inject secrets as env vars

resource "aws_iam_role_policy" "ecs_exec_secrets" {
  count  = length(var.secrets_arns) > 0 ? 1 : 0
  name   = "${local.name_prefix}-ecs-exec-secrets"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_exec_secrets[0].json
}

data "aws_iam_policy_document" "ecs_exec_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0

  statement {
    sid    = "SecretsRead"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = var.secrets_arns
  }
}

# KMS decrypt – for encrypted secrets or ECR images

resource "aws_iam_role_policy" "ecs_exec_kms" {
  count  = length(var.kms_key_arns) > 0 ? 1 : 0
  name   = "${local.name_prefix}-ecs-exec-kms"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_exec_kms[0].json
}

data "aws_iam_policy_document" "ecs_exec_kms" {
  count = length(var.kms_key_arns) > 0 ? 1 : 0

  statement {
    sid       = "KMSDecrypt"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = var.kms_key_arns
  }
}

###########################################################
# 2. ECS Task Role
#    – Application-level permissions for running containers
###########################################################

data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    sid     = "ECSTaskAssume"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
  tags               = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-task" })
}

# S3 access – scoped to provided bucket ARNs

resource "aws_iam_role_policy" "ecs_task_s3" {
  count  = length(var.s3_bucket_arns) > 0 ? 1 : 0
  name   = "${local.name_prefix}-ecs-task-s3"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_s3[0].json
}

data "aws_iam_policy_document" "ecs_task_s3" {
  count = length(var.s3_bucket_arns) > 0 ? 1 : 0

  statement {
    sid    = "S3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:DeleteObject",
      "s3:GetBucketLocation",
    ]
    resources = local.s3_resource_arns
  }
}

# SQS access – scoped to provided queue ARNs

resource "aws_iam_role_policy" "ecs_task_sqs" {
  count  = length(var.sqs_queue_arns) > 0 ? 1 : 0
  name   = "${local.name_prefix}-ecs-task-sqs"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_sqs[0].json
}

data "aws_iam_policy_document" "ecs_task_sqs" {
  count = length(var.sqs_queue_arns) > 0 ? 1 : 0

  statement {
    sid    = "SQSAccess"
    effect = "Allow"
    actions = [
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes",
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
    ]
    resources = var.sqs_queue_arns
  }
}

# SNS publish – scoped to provided topic ARNs

resource "aws_iam_role_policy" "ecs_task_sns" {
  count  = length(var.sns_topic_arns) > 0 ? 1 : 0
  name   = "${local.name_prefix}-ecs-task-sns"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_sns[0].json
}

data "aws_iam_policy_document" "ecs_task_sns" {
  count = length(var.sns_topic_arns) > 0 ? 1 : 0

  statement {
    sid    = "SNSPublish"
    effect = "Allow"
    actions = [
      "sns:Publish",
    ]
    resources = var.sns_topic_arns
  }
}

# Secrets Manager read – application-level secret access

resource "aws_iam_role_policy" "ecs_task_secrets" {
  count  = length(var.secrets_arns) > 0 ? 1 : 0
  name   = "${local.name_prefix}-ecs-task-secrets"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_secrets[0].json
}

data "aws_iam_policy_document" "ecs_task_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0

  statement {
    sid    = "SecretsManagerRead"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = var.secrets_arns
  }
}

# DynamoDB access – scoped to project-prefixed tables

data "aws_iam_policy_document" "ecs_task_dynamodb" {
  statement {
    sid    = "DynamoDBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [
      local.dynamodb_table_arn,
      "${local.dynamodb_table_arn}/index/*",
    ]
  }
}

resource "aws_iam_role_policy" "ecs_task_dynamodb" {
  name   = "${local.name_prefix}-ecs-task-dynamodb"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_dynamodb.json
}

# KMS decrypt/encrypt – for application-level encryption

resource "aws_iam_role_policy" "ecs_task_kms" {
  count  = length(var.kms_key_arns) > 0 ? 1 : 0
  name   = "${local.name_prefix}-ecs-task-kms"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_kms[0].json
}

data "aws_iam_policy_document" "ecs_task_kms" {
  count = length(var.kms_key_arns) > 0 ? 1 : 0

  statement {
    sid    = "KMSEncryptDecrypt"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
    ]
    resources = var.kms_key_arns
  }
}

###########################################################
# 3. GitHub Actions OIDC Provider (conditional)
###########################################################

resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 1 : 0

  url            = local.github_oidc_url
  client_id_list = ["sts.amazonaws.com"]

  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-github-oidc" })
}

###########################################################
# 4. GitHub Actions Deployment Role (conditional)
###########################################################

locals {
  oidc_provider_arn = var.create_oidc_provider ? (
    length(aws_iam_openid_connect_provider.github) > 0
    ? aws_iam_openid_connect_provider.github[0].arn
    : ""
    ) : (
    "arn:aws:iam::${var.account_id}:oidc-provider/token.actions.githubusercontent.com"
  )

  create_github_role = var.github_org != "" && var.github_repo != ""

  github_subject_patterns = length(var.github_allowed_subjects) > 0 ? var.github_allowed_subjects : ["repo:${var.github_org}/${var.github_repo}:*"]
}

data "aws_iam_policy_document" "github_actions_assume" {
  count = local.create_github_role ? 1 : 0

  statement {
    sid     = "GitHubActionsOIDCAssume"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.github_subject_patterns
    }
  }
}

resource "aws_iam_role" "github_actions" {
  count = local.create_github_role ? 1 : 0

  name                 = var.github_actions_role_name != "" ? var.github_actions_role_name : "${local.name_prefix}-github-actions-deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_actions_assume[0].json
  max_session_duration = 3600

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-github-actions-deploy" })
}

# ECR push permissions for CI/CD

data "aws_iam_policy_document" "gha_ecr" {
  count = local.create_github_role ? 1 : 0

  statement {
    sid    = "ECRAuth"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECRPushPull"
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeRepositories",
      "ecr:ListImages",
    ]
    resources = var.ecr_repository_arns
  }
}

resource "aws_iam_role_policy" "gha_ecr" {
  count  = local.create_github_role ? 1 : 0
  name   = "${local.name_prefix}-gha-ecr"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.gha_ecr[0].json
}

# ECS deployment permissions

data "aws_iam_policy_document" "gha_ecs" {
  count = local.create_github_role ? 1 : 0

  statement {
    sid    = "ECSDeployServices"
    effect = "Allow"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition",
      "ecs:DeregisterTaskDefinition",
      "ecs:ListTasks",
      "ecs:DescribeTasks",
      "ecs:ListServices",
      "ecs:DescribeClusters",
    ]
    resources = [
      "arn:aws:ecs:${var.region}:${var.account_id}:cluster/${local.name_prefix}-*",
      "arn:aws:ecs:${var.region}:${var.account_id}:service/${local.name_prefix}-*/*",
      "arn:aws:ecs:${var.region}:${var.account_id}:task/${local.name_prefix}-*/*",
      "arn:aws:ecs:${var.region}:${var.account_id}:task-definition/${local.name_prefix}-*:*",
    ]
  }

  statement {
    sid    = "PassRoleToECS"
    effect = "Allow"
    actions = [
      "iam:PassRole",
    ]
    resources = [
      aws_iam_role.ecs_task_execution.arn,
      aws_iam_role.ecs_task.arn,
    ]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "gha_ecs" {
  count  = local.create_github_role ? 1 : 0
  name   = "${local.name_prefix}-gha-ecs"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.gha_ecs[0].json
}

# Terraform state backend permissions (S3 + DynamoDB lock table)

data "aws_iam_policy_document" "gha_terraform" {
  count = local.create_github_role ? 1 : 0

  statement {
    sid    = "TerraformStateS3"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketVersioning",
      "s3:GetBucketLocation",
    ]
    resources = [
      "arn:aws:s3:::${local.terraform_state_bucket_name}",
      "arn:aws:s3:::${local.terraform_state_bucket_name}/*",
    ]
  }

  statement {
    sid    = "TerraformLockDynamoDB"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
    ]
    resources = [
      "arn:aws:dynamodb:${var.region}:${var.account_id}:table/${local.terraform_lock_table_name}",
    ]
  }
}

resource "aws_iam_role_policy" "gha_terraform" {
  count  = local.create_github_role ? 1 : 0
  name   = "${local.name_prefix}-gha-terraform"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.gha_terraform[0].json
}

# Terraform apply permissions (broad but limited to the services this stack uses).
# NOTE: This replaces the need for ad-hoc console policies on the role.

data "aws_iam_policy_document" "gha_terraform_apply" {
  count = local.create_github_role ? 1 : 0

  statement {
    sid    = "TerraformApply"
    effect = "Allow"
    actions = [
      "acm:*",
      "cloudfront:*",
      "cloudwatch:*",
      "cognito-idp:*",
      "dynamodb:*",
      "ec2:*",
      "ecr:*",
      "ecs:*",
      "elasticache:*",
      "elasticloadbalancing:*",
      "iam:AttachRolePolicy",
      "iam:CreatePolicy",
      "iam:CreatePolicyVersion",
      "iam:CreateRole",
      "iam:CreateServiceLinkedRole",
      "iam:DeletePolicy",
      "iam:DeletePolicyVersion",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:DetachRolePolicy",
      "iam:Get*",
      "iam:List*",
      "iam:PassRole",
      "iam:PutRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:UpdateRole",
      "kms:*",
      "logs:*",
      "rds:*",
      "route53:*",
      "s3:*",
      "secretsmanager:*",
      "sns:*",
      "wafv2:*",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "gha_terraform_apply" {
  count  = local.create_github_role ? 1 : 0
  name   = "${local.name_prefix}-gha-terraform-apply"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.gha_terraform_apply[0].json
}

# CloudWatch Logs read  for deployment verification

data "aws_iam_policy_document" "gha_logs" {
  count = local.create_github_role ? 1 : 0

  statement {
    sid    = "CloudWatchLogsRead"
    effect = "Allow"
    actions = [
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:GetLogEvents",
    ]
    resources = [
      local.log_group_arn_prefix,
      "${local.log_group_arn_prefix}:log-stream:*",
      "${local.log_group_arn_prefix}-*",
      "${local.log_group_arn_prefix}-*:log-stream:*",
    ]
  }
}

resource "aws_iam_role_policy" "gha_logs" {
  count  = local.create_github_role ? 1 : 0
  name   = "${local.name_prefix}-gha-logs"
  role   = aws_iam_role.github_actions[0].id
  policy = data.aws_iam_policy_document.gha_logs[0].json
}
