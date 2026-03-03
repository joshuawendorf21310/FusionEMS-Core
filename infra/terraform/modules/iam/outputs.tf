############################################################
# IAM Module – Outputs
############################################################

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions deployment role (empty when OIDC is not configured)"
  value       = length(aws_iam_role.github_actions) > 0 ? aws_iam_role.github_actions[0].arn : ""
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider (empty when not created)"
  value       = length(aws_iam_openid_connect_provider.github) > 0 ? aws_iam_openid_connect_provider.github[0].arn : ""
}
