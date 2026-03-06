output "queue_urls" {
  description = "Map of queue name to its URL"
  value       = { for k, q in aws_sqs_queue.main : k => q.url }
}

output "queue_arns" {
  description = "Map of queue name to its ARN"
  value       = { for k, q in aws_sqs_queue.main : k => q.arn }
}

output "dlq_urls" {
  description = "Map of queue name to its dead-letter queue URL"
  value       = { for k, q in aws_sqs_queue.dlq : k => q.url }
}

output "dlq_arns" {
  description = "Map of queue name to its dead-letter queue ARN"
  value       = { for k, q in aws_sqs_queue.dlq : k => q.arn }
}
