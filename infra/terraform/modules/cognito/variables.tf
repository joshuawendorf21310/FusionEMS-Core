variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
}

variable "project" {
  description = "Project / application name used in resource naming"
  type        = string
}

variable "callback_urls" {
  description = "List of allowed callback URLs for the Cognito app client"
  type        = list(string)
}

variable "logout_urls" {
  description = "List of allowed logout URLs for the Cognito app client"
  type        = list(string)
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}
