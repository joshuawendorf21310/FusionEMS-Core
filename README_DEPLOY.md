# FusionEMS Quantum - Deployment & Operations Runbook

## Architecture Overview

Terraform-only IaC. No CloudFormation. OIDC for GitHub Actions. Secrets Manager for all vendor keys.

| Component | Technology | Notes |
|-----------|-----------|-------|
| IaC | Terraform 1.8.5 | S3 backend + DynamoDB lock |
| CI/CD | GitHub Actions | OIDC, no static AWS keys |
| Compute | ECS Fargate | Private subnets, NAT outbound |
| Database | RDS PostgreSQL 16 | Multi-AZ prod, encrypted |
| Cache | ElastiCache Redis 7 | Failover enabled, auth token |
| CDN | CloudFront | WAF attached, HTTP/2+3 |
| DNS | Route53 | Zone: fusionemsquantum.com |
| Auth | Cognito | MFA enforced in prod |
| Secrets | AWS Secrets Manager | Vendor-scoped, KMS encrypted |
| Monitoring | CloudWatch + OTel | SNS alerts, dashboards |

## Prerequisites

- AWS CLI v2 configured
- Terraform 1.8.5+
- GitHub CLI (`gh`)
- Docker

## Bootstrap (First-Time Setup)

### 1. Create S3 State Bucket + DynamoDB Lock Table

```bash
./bootstrap.sh
```

This creates:
- `fusionems-terraform-state-{dev,staging,prod,dr}` S3 buckets with versioning
- `fusionems-terraform-locks` DynamoDB table
- GitHub Actions OIDC provider
- IAM deploy role

### 2. Configure GitHub Repository

Set these GitHub Variables (Settings > Variables):
- `AWS_ACCOUNT_ID`: Your AWS account ID
- `AWS_OIDC_ROLE_ARN`: `arn:aws:iam::<ACCOUNT>:role/fusionems-github-actions-deploy`

Create a `prod` Environment (Settings > Environments):
- Add required reviewers (founder/admin)
- Restrict to `main` branch

### 3. Populate Secrets

```bash
aws secretsmanager put-secret-value \
  --secret-id fusionems-prod/vendors/stripe \
  --secret-string '{"secret_key":"sk_live_...","publishable_key":"pk_live_...","webhook_secret":"whsec_..."}'

aws secretsmanager put-secret-value \
  --secret-id fusionems-prod/vendors/telnyx \
  --secret-string '{"api_key":"KEY...","public_key":"...","webhook_tolerance_seconds":"300"}'

aws secretsmanager put-secret-value \
  --secret-id fusionems-prod/vendors/lob \
  --secret-string '{"api_key":"live_...","webhook_secret":"..."}'

aws secretsmanager put-secret-value \
  --secret-id fusionems-prod/vendors/openai \
  --secret-string '{"api_key":"sk-...","org_id":"org-..."}'

aws secretsmanager put-secret-value \
  --secret-id fusionems-prod/vendors/officeally \
  --secret-string '{"sftp_host":"...","sftp_port":"22","sftp_username":"...","sftp_password":"...","sftp_remote_dir":"/"}'
```

### 4. Deploy Infrastructure

```bash
cd infra/terraform/environments/prod
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 5. Founder Bootstrap

```bash
python -m backend.core_app.founder.bootstrap --email founder@fusionemsquantum.com
```

The founder must:
1. Log in with the temporary password from Secrets Manager
2. Change password immediately
3. Enroll TOTP MFA (mandatory)

## CI/CD Pipeline

### Pull Request Flow

1. Push to branch, open PR targeting `main`
2. Pipeline runs: fmt, init, validate, plan, tfsec, Checkov, OPA, Trivy
3. Plan output posted as PR comment
4. Destructive changes blocked unless `approve-destroy` label added
5. Infracost runs if API key configured

### Merge to Main

1. `validate_plan` runs again
2. `apply_prod` requires `prod` environment approval
3. Terraform apply executes with lock timeout

### Drift Detection

Nightly at 03:00 UTC. Opens GitHub issue if drift detected.

## Domain Configuration

| Domain | Target | Purpose |
|--------|--------|---------|
| `fusionemsquantum.com` | CloudFront (301 -> www) | Apex redirect |
| `www.fusionemsquantum.com` | CloudFront -> ALB | Homepage |
| `api.fusionemsquantum.com` | CloudFront -> ALB | API |

ACM certificate SANs: `fusionemsquantum.com`, `www.fusionemsquantum.com`, `api.fusionemsquantum.com`

## Secrets Management

All secrets in AWS Secrets Manager. Never in GitHub, Terraform variables, or state.

| Secret Path | Purpose |
|-------------|---------|
| `fusionems-prod/vendors/stripe` | Stripe API keys |
| `fusionems-prod/vendors/telnyx` | Telnyx API keys |
| `fusionems-prod/vendors/lob` | Lob API keys |
| `fusionems-prod/vendors/openai` | OpenAI API keys |
| `fusionems-prod/vendors/officeally` | Office Ally SFTP |
| `fusionems-prod/app/config` | Application config |
| `fusionems-prod/founder/bootstrap` | Founder break-glass |

Runtime injection: ECS task definitions reference Secrets Manager ARNs.

## Rollback / Recovery

### Terraform Rollback

```bash
cd infra/terraform/environments/prod
git log --oneline infra/terraform/  # find last good commit
git checkout <commit> -- infra/terraform/
terraform init
terraform plan  # verify rollback plan
terraform apply
```

### ECS Service Rollback

```bash
python scripts/ecs_update_service.py \
  --cluster fusionems-prod \
  --service backend \
  --region us-east-1
```

### Database Recovery

RDS automated backups: 7-day retention. Point-in-time recovery available.

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier fusionems-prod-db \
  --target-db-instance-identifier fusionems-prod-db-recovery \
  --restore-time <ISO-8601-timestamp>
```

### Redis Recovery

ElastiCache snapshots: 7-day retention.

## NEMSIS Integration

Status: **NEMSIS-ready / validation-passing** (not certified)

- NEMSIS v3.5.1 XSD validation
- Wisconsin state profile (WARDS Elite submission adapter)
- CI validation harness: `python -m backend.compliance.nemsis.ci_validate`
- Certification tracking: Pending formal NEMSIS compliance process

## NERIS Integration

Status: **NERIS integration-ready / validation-passing** (not certified)

- Schema adapter with entity/incident mappings
- SQS publish queue for incident exports
- CAD linkage support
- CI validation: `python -m backend.compliance.neris.ci_validate`

## Operational Checklists

### Pre-Deploy

- [ ] All CI checks pass (fmt, validate, tfsec, Checkov, OPA)
- [ ] Plan reviewed, no unexpected destructive changes
- [ ] Secrets populated in target environment
- [ ] Database migrations applied
- [ ] Prod environment approval obtained

### Post-Deploy

- [ ] Health endpoints responding: `/healthz`, `/api/v1/health`
- [ ] CloudFront distribution deployed, www resolves
- [ ] Apex domain redirects to www
- [ ] WAF rules active (check CloudWatch WAF logs)
- [ ] ECS services stable (desired count matches running)
- [ ] RDS connectivity verified
- [ ] Redis connectivity verified

### Incident Response

1. Check CloudWatch alarms and SNS notifications
2. Review ECS service events: `aws ecs describe-services`
3. Check application logs in CloudWatch Logs
4. If database issue: check RDS events and performance insights
5. If network issue: check VPC flow logs
6. Rollback if necessary using procedures above

## Security Posture

Enterprise Infrastructure Maturity Level 4/5 (sovereign-grade engineering posture).

Implemented:
- Zero static AWS credentials (OIDC only)
- Centralized secrets (Secrets Manager, KMS encrypted)
- Hardened CI/CD (tfsec, Checkov, OPA, Trivy, destructive-change detection)
- WAF on CloudFront (managed rules, rate limiting, SQLi protection)
- Encryption at rest (KMS) and in transit (TLS 1.2+)
- Private subnets for all workloads
- Continuous vulnerability scanning
- Audit logging

Not implemented (explicit exclusions):
- SCP guardrails
- Dedicated deploy account
- Customer-managed KMS everywhere
- Immutable artifact signing
- CloudTrail log integrity validation
- Continuous compliance reporting
- FedRAMP 3PAO/ATO
- GovCloud boundary
