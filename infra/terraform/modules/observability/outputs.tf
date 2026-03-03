output "alert_topic_arn" {
  description = "ARN of the SNS topic for CloudWatch alarm notifications"
  value       = aws_sns_topic.alerts.arn
}

output "dashboard_name" {
  description = "Name of the CloudWatch ops dashboard"
  value       = aws_cloudwatch_dashboard.ops.dashboard_name
}

output "audit_log_group_name" {
  description = "Name of the audit CloudWatch log group"
  value       = aws_cloudwatch_log_group.audit.name
}

output "audit_log_group_arn" {
  description = "ARN of the audit CloudWatch log group"
  value       = aws_cloudwatch_log_group.audit.arn
}
