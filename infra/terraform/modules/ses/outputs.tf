output "graph_email_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Graph email credentials"
  value       = aws_secretsmanager_secret.graph_email.arn
}

output "graph_email_access_policy_arn" {
  description = "ARN of the IAM policy granting access to the Graph email secret"
  value       = aws_iam_policy.graph_email_access.arn
}
