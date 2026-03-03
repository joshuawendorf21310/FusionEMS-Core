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

variable "root_domain_name" {
  description = "Root domain name for the CloudFront distribution (e.g. example.com)"
  type        = string
}

variable "api_domain_name" {
  description = "API domain name for the CloudFront distribution (e.g. api.example.com)"
  type        = string
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID for DNS records"
  type        = string
}

variable "acm_certificate_arn_us_east_1" {
  description = "ARN of the ACM certificate in us-east-1 for CloudFront"
  type        = string
}

variable "alb_dns_name" {
  description = "DNS name of the Application Load Balancer origin"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
