############################################################
# IAM Module – Variables
############################################################

variable "environment" {
  description = "Deployment environment (dev, staging, prod, dr)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "environment must be one of: dev, staging, prod, dr"
  }
}

variable "project" {
  description = "Project name used in resource naming"
  type        = string
  default     = "fusionems"
}

variable "region" {
  description = "AWS region for scoping resource ARNs"
  type        = string
}

variable "account_id" {
  description = "AWS account ID for scoping resource ARNs"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be a 12-digit AWS account ID"
  }
}

# ── GitHub Actions OIDC ──────────────────────────────────

variable "create_oidc_provider" {
  description = "Whether to create the GitHub Actions OIDC provider (only once per account)"
  type        = bool
  default     = false
}

variable "github_org" {
  description = "GitHub organisation that owns the repository"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (without org prefix)"
  type        = string
}

variable "github_actions_role_name" {
  description = "Optional override for the GitHub Actions deployment role name (defaults to <project>-<env>-github-actions-deploy)"
  type        = string
  default     = ""
}

variable "github_allowed_subjects" {
  description = "Optional allowed GitHub OIDC subject patterns (sub). If empty, defaults to repo:<org>/<repo>:*"
  type        = list(string)
  default     = []
}

# ── Resource ARN scoping ─────────────────────────────────

variable "ecr_repository_arns" {
  description = "ARNs of ECR repositories the execution role may pull from"
  type        = list(string)
}

variable "s3_bucket_arns" {
  description = "ARNs of S3 buckets the ECS task role may access"
  type        = list(string)
}

variable "sqs_queue_arns" {
  description = "ARNs of SQS queues the ECS task role may access"
  type        = list(string)
  default     = []
}

variable "sns_topic_arns" {
  description = "ARNs of SNS topics the ECS task role may publish to"
  type        = list(string)
  default     = []
}

variable "secrets_arns" {
  description = "ARNs of Secrets Manager secrets the ECS task role may read"
  type        = list(string)
  default     = []
}

variable "kms_key_arns" {
  description = "ARNs of KMS keys the ECS task role may use for decrypt/encrypt"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional tags to merge with common tags"
  type        = map(string)
  default     = {}
}
