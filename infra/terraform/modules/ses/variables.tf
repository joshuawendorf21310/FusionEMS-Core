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

variable "graph_tenant_id" {
  description = "Microsoft Graph tenant ID"
  type        = string
  sensitive   = true
}

variable "graph_client_id" {
  description = "Microsoft Graph client ID"
  type        = string
  sensitive   = true
}

variable "graph_client_secret" {
  description = "Microsoft Graph client secret"
  type        = string
  sensitive   = true
}

variable "graph_founder_email" {
  description = "Founder email address for Graph API send-as"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
