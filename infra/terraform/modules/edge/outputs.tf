output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.id
}

output "cloudfront_hosted_zone_id" {
  description = "Hosted zone ID of the CloudFront distribution (for Route 53 alias records)"
  value       = aws_cloudfront_distribution.this.hosted_zone_id
}
