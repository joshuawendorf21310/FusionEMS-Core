output "certificate_arn" {
  description = "ARN of the validated ACM certificate"
  value       = aws_acm_certificate.this.arn
}

output "certificate_domain_name" {
  description = "Primary domain name of the ACM certificate"
  value       = aws_acm_certificate.this.domain_name
}
