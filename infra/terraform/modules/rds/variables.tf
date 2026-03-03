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

variable "vpc_id" {
  description = "VPC ID where the RDS instance will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the DB subnet group"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID of the ECS service allowed to connect"
  type        = string
}

variable "rds_security_group_id" {
  description = "Security group ID to attach to the RDS instance"
  type        = string
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.large"
}

variable "db_name" {
  description = "Name of the initial database"
  type        = string
  default     = "fusionems"
}

variable "db_username" {
  description = "Master username for the RDS instance"
  type        = string
  default     = "fusionems_admin"
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
