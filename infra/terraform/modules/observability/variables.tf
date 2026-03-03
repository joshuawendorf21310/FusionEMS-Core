variable "environment" {
  description = "Deployment environment (dev, staging, prod, dr)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}

variable "project" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "fusionems"
}

variable "alert_email" {
  description = "Email address to receive CloudWatch alarm notifications"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster to monitor"
  type        = string
}

variable "backend_service_name" {
  description = "Name of the backend ECS service to monitor"
  type        = string
}

variable "alb_arn_suffix" {
  description = "ARN suffix of the Application Load Balancer"
  type        = string
}

variable "backend_target_group_arn_suffix" {
  description = "ARN suffix of the backend target group"
  type        = string
}

variable "db_instance_id" {
  description = "Identifier of the RDS instance to monitor"
  type        = string
}

variable "redis_cluster_id" {
  description = "Replication group ID of the Redis cluster to monitor"
  type        = string
}

variable "log_retention_days" {
  description = "Number of days to retain audit log events"
  type        = number
  default     = 30
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for SNS topic and log group encryption"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
