output "queue_urls" {
  description = "Map of queue name to SQS queue URL"
  value       = { for k, v in aws_sqs_queue.main : k => v.url }
}

output "queue_arns" {
  description = "Map of queue name to SQS queue ARN"
  value       = { for k, v in aws_sqs_queue.main : k => v.arn }
}

output "dlq_arns" {
  description = "Map of queue name to dead-letter queue ARN"
  value       = { for k, v in aws_sqs_queue.dlq : k => v.arn }
}

output "all_queue_arns" {
  description = "List of all queue ARNs (main + DLQ) for IAM policy attachment"
  value = concat(
    [for v in aws_sqs_queue.main : v.arn],
    [for v in aws_sqs_queue.dlq : v.arn],
  )
}
