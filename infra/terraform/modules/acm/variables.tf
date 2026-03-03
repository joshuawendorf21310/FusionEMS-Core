variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
}

variable "project" {
  description = "Project / application name used in resource naming"
  type        = string
}

variable "root_domain_name" {
  description = "Primary domain name for the certificate"
  type        = string
}

variable "api_domain_name" {
  description = "API domain name added as a Subject Alternative Name"
  type        = string
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID used for DNS validation"
  type        = string
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}
