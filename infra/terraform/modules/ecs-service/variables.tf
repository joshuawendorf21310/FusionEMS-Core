variable "environment" {
  description = "Deployment environment"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}

variable "project" {
  description = "Project name used for resource naming"
  type        = string
  default     = "fusionems"
}

variable "service_name" {
  description = "Name of the ECS service (e.g. billing, cad, epcr)"
  type        = string
}

variable "cluster_id" {
  description = "ID of the ECS cluster"
  type        = string
}

variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where resources are deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for task placement"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs attached to the ECS tasks"
  type        = list(string)
}

variable "execution_role_arn" {
  description = "ARN of the ECS task execution IAM role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the ECS task IAM role"
  type        = string
}

variable "container_image" {
  description = "Docker image URI for the container"
  type        = string
}

variable "container_port" {
  description = "Port exposed by the container"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "CPU units for the Fargate task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "memory" {
  description = "Memory in MiB for the Fargate task"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired number of running tasks"
  type        = number
  default     = 2
}

variable "deployment_minimum_healthy_percent" {
  description = "Minimum percentage of tasks that must remain healthy during a deployment"
  type        = number
  default     = 100

  validation {
    condition     = var.deployment_minimum_healthy_percent >= 0 && var.deployment_minimum_healthy_percent <= 100
    error_message = "deployment_minimum_healthy_percent must be between 0 and 100."
  }
}

variable "min_capacity" {
  description = "Minimum number of tasks for autoscaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks for autoscaling"
  type        = number
  default     = 10
}

variable "health_check_path" {
  description = "HTTP path for target group health checks"
  type        = string
  default     = "/health"
}

variable "container_healthcheck_command" {
  description = "Optional override for the ECS container healthcheck command. If null, defaults to using curl against localhost. Example: [\"CMD-SHELL\", \"node -e '...'\"]"
  type        = list(string)
  default     = null
}

variable "health_check_interval" {
  description = "Interval in seconds between health checks"
  type        = number
  default     = 30
}

variable "alb_listener_arn" {
  description = "ARN of the ALB listener to attach the rule to"
  type        = string
}

variable "additional_alb_listener_arns" {
  description = "Additional ALB listener ARNs to attach the same listener rule to (e.g., an HTTP listener for CloudFront origin traffic). Use a map so keys are known at plan time."
  type        = map(string)
  default     = {}
}

variable "path_pattern" {
  description = "URL path patterns for the listener rule"
  type        = list(string)
}

variable "listener_rule_priority" {
  description = "Priority for the ALB listener rule"
  type        = number
}

variable "environment_variables" {
  description = "Environment variables for the container"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "secrets" {
  description = "Secrets to inject from SSM/Secrets Manager"
  type = list(object({
    name      = string
    valueFrom = string
  }))
  default = []
}

variable "log_group_name" {
  description = "CloudWatch log group name for container logs"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
