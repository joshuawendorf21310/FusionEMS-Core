###############################################################################
# FusionEMS ECS Cluster Module – Variables
###############################################################################

variable "environment" {
  description = "Deployment environment"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "environment must be one of: dev, staging, prod, dr."
  }
}

variable "project" {
  description = "Project name used as a naming prefix"
  type        = string
  default     = "fusionems"
}

variable "vpc_id" {
  description = "VPC ID where resources are deployed"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for the ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID attached to the ALB"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for the HTTPS listener"
  type        = string
}

variable "waf_acl_arn" {
  description = "WAFv2 Web ACL ARN to associate with the ALB (empty to skip)"
  type        = string
  default     = ""
}

variable "enable_waf" {
  description = "Whether to associate the WAF Web ACL with the ALB (avoids plan-time unknown count)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log group retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
