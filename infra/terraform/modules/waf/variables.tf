variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
}

variable "project" {
  description = "Project / application name used in resource naming"
  type        = string
}

variable "stripe_webhook_cidrs" {
  description = "List of Stripe webhook IPv4 CIDRs to allow"
  type        = list(string)
  default     = []
}

variable "telnyx_webhook_cidrs" {
  description = "List of Telnyx webhook IPv4 CIDRs to allow"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}
