#!/usr/bin/env bash
# Continuous ECS + ALB + CloudFront + CloudWatch watcher
# Usage: export AWS_PROFILE=...; ./scripts/ecs_runtime_watch.sh <cluster> <service> <target-group-arn> <cloudfront-id> <log-group>
set -uo pipefail
cluster=${1:-$CLUSTER_NAME}
service=${2:-$SERVICE_NAME}
tg_arn=${3:-$TARGET_GROUP_ARN}
cf_id=${4:-$CLOUDFRONT_DISTRIBUTION_ID}
log_group=${5:-$LOG_GROUP_NAME}
interval=60

if [[ -z "$cluster" || -z "$service" ]]; then
  echo "Usage: $0 <cluster> <service> <target-group-arn> <cloudfront-id> <log-group>"
  exit 2
fi

while true; do
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # ECS running/desired
  ecs_counts=$(aws ecs describe-services --cluster "$cluster" --services "$service" --query 'services[0].[runningCount,desiredCount]' --output text 2>/dev/null || echo "NA NA")
  running=$(echo "$ecs_counts" | awk '{print $1}')
  desired=$(echo "$ecs_counts" | awk '{print $2}')

  # ALB target health
  if [[ -n "$tg_arn" && "$tg_arn" != "" ]]; then
    unhealthy_count=$(aws elbv2 describe-target-health --target-group-arn "$tg_arn" --query 'TargetHealthDescriptions[?TargetHealth.State!=`healthy` || TargetHealth.State==`unhealthy`]' --output json 2>/dev/null | jq '. | length' 2>/dev/null || echo "NA")
    tg_summary=$(aws elbv2 describe-target-health --target-group-arn "$tg_arn" --query 'TargetHealthDescriptions[].TargetHealth.State' --output text 2>/dev/null || echo "NA")
  else
    unhealthy_count=NA
    tg_summary=NA
  fi

  # CloudFront status
  if [[ -n "$cf_id" && "$cf_id" != "" ]]; then
    cf_status=$(aws cloudfront get-distribution --id "$cf_id" --query 'Distribution.Status' --output text 2>/dev/null || echo "NA")
  else
    cf_status=NA
  fi

  # Newest STOPPED task details
  last_task_arn=$(aws ecs list-tasks --cluster "$cluster" --service-name "$service" --desired-status STOPPED --output text --query 'taskArns' 2>/dev/null | tr '\t' '\n' | tail -n 1 || echo "")
  if [[ -n "$last_task_arn" ]]; then
    stopped_reason=$(aws ecs describe-tasks --cluster "$cluster" --tasks "$last_task_arn" --query 'tasks[0].stoppedReason' --output text 2>/dev/null || echo "")
    containers_info=$(aws ecs describe-tasks --cluster "$cluster" --tasks "$last_task_arn" --query 'tasks[0].containers[].{name:name,exitCode:exitCode,lastStatus:lastStatus,reason:reason}' --output json 2>/dev/null || echo "[]")
    last_error_msg="$stopped_reason"
    if [[ -z "$last_error_msg" || "$last_error_msg" == "None" ]]; then
      last_error_msg=$(echo "$containers_info" | jq -r '.[0] | if .reason then .reason else ("exitCode=" + (.exitCode|tostring)) end' 2>/dev/null || echo "")
    fi
  else
    last_error_msg="(no stopped tasks found)"
  fi

  # Newest CloudWatch logs message (best-effort)
  if [[ -n "$log_group" && "$log_group" != "" ]]; then
    newest_log=$(aws logs filter-log-events --log-group-name "$log_group" --limit 1 --query 'events[0].message' --output text 2>/dev/null || echo "(no logs)")
  else
    newest_log="(no log_group provided)"
  fi

  # Decide single next action heuristic
  next_action="No action"
  if [[ "$running" == "NA" || "$desired" == "NA" ]]; then
    next_action="Unable to determine ECS counts — check AWS credentials/permissions"
  elif [[ "$running" -lt "$desired" ]]; then
    next_action="Investigate task placement or startup errors (inspect container logs); consider forcing a new deployment"
  elif [[ "$unhealthy_count" != "NA" && "$unhealthy_count" -gt 0 ]]; then
    next_action="Investigate ALB target health and app readiness (check container /health endpoints and security groups)"
  elif [[ -n "$last_task_arn" && "$last_error_msg" != "(no stopped tasks found)" && "$last_error_msg" != "" ]]; then
    next_action="Inspect logs for the most recent stopped task: $last_task_arn"
  elif [[ "$cf_status" != "Deployed" && "$cf_status" != "NA" ]]; then
    next_action="CloudFront status is $cf_status — wait for distribution to finish or check invalidation status"
  fi

  # Output a compact report
  cat <<EOF
[$timestamp] ECS Watch Report
  Cluster: $cluster  Service: $service
  Running/Desired: ${running:-NA}/${desired:-NA}
  ALB target summary: ${tg_summary}
  ALB unhealthy count: ${unhealthy_count}
  CloudFront status: ${cf_status}
  Newest stopped-task message: ${last_error_msg}
  Newest log message (CW): ${newest_log}
  Single next action: ${next_action}
EOF

  sleep $interval
done
