###############################################################################
# FusionEMS – Input variables (shared across all environments)
###############################################################################

# ─── General ─────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod, dr)"
  type        = string
}

variable "project" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "fusionems"
}

# ─── Networking ──────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones to deploy into"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
}

# ─── DNS / TLS ───────────────────────────────────────────────────────────────

variable "root_domain_name" {
  description = "Root domain name for the application"
  type        = string
}

variable "api_domain_name" {
  description = "API domain name"
  type        = string
}

variable "app_domain_name" {
  description = "App (frontend) domain name"
  type        = string
  default     = "app.fusionemsquantum.com"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for DNS records"
  type        = string
}

variable "acm_certificate_arn_us_east_1" {
  description = "ACM certificate ARN in us-east-1 (required for CloudFront)"
  type        = string
  default     = ""
}

# ─── Monitoring ──────────────────────────────────────────────────────────────

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
}

# ─── Container Images ───────────────────────────────────────────────────────

variable "backend_image_tag" {
  description = "Docker image tag for the backend service"
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Docker image tag for the frontend service"
  type        = string
  default     = "latest"
}

# ─── CI / CD ─────────────────────────────────────────────────────────────────

variable "github_org" {
  description = "GitHub organization for OIDC federation"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name for OIDC federation"
  type        = string
  default     = ""
}

variable "github_actions_role_name" {
  description = "Role name GitHub Actions should assume for Terraform deployments"
  type        = string
  default     = ""
}

variable "github_allowed_subjects" {
  description = "Allowed GitHub OIDC subject patterns for the deployment role trust policy"
  type        = list(string)
  default     = []
}

variable "stripe_webhook_cidrs" {
  description = "List of Stripe webhook IPv4 CIDRs to allow at WAF"
  type        = list(string)
  default     = []
}

variable "telnyx_webhook_cidrs" {
  description = "List of Telnyx webhook IPv4 CIDRs to allow at WAF"
  type        = list(string)
  default     = []
}

variable "lob_webhook_cidrs" {
  description = "List of Lob webhook IPv4 CIDRs to allow at WAF"
  type        = list(string)
  default     = []
}

# ─── Database ────────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
}

# ─── Cache ───────────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
}

# ─── SES / Microsoft Graph ──────────────────────────────────────────────────

variable "graph_tenant_id" {
  description = "Microsoft Graph tenant ID for email integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "graph_client_id" {
  description = "Microsoft Graph client ID for email integration"
  type        = string
  sensitive   = true
  default     = ""
}
