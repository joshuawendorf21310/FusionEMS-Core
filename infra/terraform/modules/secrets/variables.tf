variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "fusionems"
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
