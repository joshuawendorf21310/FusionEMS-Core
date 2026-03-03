output "vendor_secret_arns" {
  description = "Map of vendor name to Secrets Manager ARN"
  value       = { for k, v in aws_secretsmanager_secret.vendor : k => v.arn }
}

output "app_secret_arn" {
  description = "Application config secret ARN"
  value       = aws_secretsmanager_secret.app.arn
}

output "founder_secret_arn" {
  description = "Founder bootstrap secret ARN"
  value       = aws_secretsmanager_secret.founder.arn
}

output "kms_key_arn" {
  description = "KMS key ARN for secrets encryption"
  value       = aws_kms_key.secrets.arn
}

output "all_secret_arns" {
  description = "List of all secret ARNs for IAM policy attachment"
  value = concat(
    [for v in aws_secretsmanager_secret.vendor : v.arn],
    [aws_secretsmanager_secret.app.arn],
    [aws_secretsmanager_secret.founder.arn],
  )
}
