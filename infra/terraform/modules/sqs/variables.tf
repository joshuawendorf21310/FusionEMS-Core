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

variable "queues" {
  description = "Map of queue definitions to create with their DLQs"
  type = map(object({
    visibility_timeout_seconds = optional(number, 120)
    message_retention_seconds  = optional(number, 1209600)
    receive_wait_time_seconds  = optional(number, 20)
    max_receive_count          = optional(number, 5)
  }))
  default = {}
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}
