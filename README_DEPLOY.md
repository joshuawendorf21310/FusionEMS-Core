# FusionEMS Deployment Guide

## Architecture Overview

FusionEMS is a multi-region AWS SaaS platform for EMS, fire, and CAD operations. Infrastructure is fully managed by Terraform with automated CI/CD through GitHub Actions.

**Core stack:**

| Layer         | Service                                      |
|---------------|----------------------------------------------|
| Compute       | ECS Fargate (backend: FastAPI, frontend: Next.js) |
| Database      | RDS PostgreSQL 16 with PostGIS               |
| Cache         | ElastiCache Redis 7                          |
| CDN           | CloudFront with WAF                          |
| DNS           | Route 53                                     |
| Auth          | Cognito user pools                           |
| Email         | SES (Microsoft Graph integration)            |
| Certificates  | ACM (auto-renewed)                           |
| Observability | CloudWatch, Prometheus, Grafana, OTEL        |
| Security      | WAF, KMS, GuardDuty, CloudTrail              |

---

## Prerequisites

| Tool          | Version    | Purpose                          |
|---------------|------------|----------------------------------|
| AWS CLI       | v2+        | Infrastructure provisioning      |
| Terraform     | >= 1.6     | IaC engine                       |
| Docker        | Latest     | Container builds                 |
| jq            | Latest     | JSON processing in scripts       |
| GitHub repo   | —          | Actions enabled, OIDC configured |

Verify your setup:

```bash
aws --version          # aws-cli/2.x
terraform -version     # Terraform v1.6+
docker --version
jq --version
aws sts get-caller-identity   # confirms credentials
```

---

## Quick Start

```bash
# 1. Bootstrap AWS resources (state buckets, lock table, OIDC, IAM role)
./bootstrap.sh --org <github-org> --repo <github-repo>

# 2. Add the deploy role ARN as a GitHub Actions secret
#    Settings → Secrets → Actions → New repository secret
#    Name:  AWS_ROLE_TO_ASSUME
#    Value: <role ARN from bootstrap output>

# 3. Push to main — CI/CD handles the rest
git push origin main
```

---

## Bootstrap

The `bootstrap.sh` script provisions all prerequisite AWS resources needed before Terraform can run. It is **idempotent** — safe to re-run.

### Usage

```bash
./bootstrap.sh --org <github-org> --repo <github-repo> [--region us-east-1]
```

| Argument   | Required | Default      | Description                  |
|------------|----------|--------------|------------------------------|
| `--org`    | Yes      | —            | GitHub organization name     |
| `--repo`   | Yes      | —            | GitHub repository name       |
| `--region` | No       | `us-east-1`  | AWS region for resources     |

### What It Creates

1. **S3 state buckets** (one per environment):
   - `fusionems-terraform-state-dev`
   - `fusionems-terraform-state-staging`
   - `fusionems-terraform-state-prod`
   - `fusionems-terraform-state-dr`
   - Versioning enabled, public access blocked, AES-256 encryption, TLS-only policy

2. **DynamoDB lock table**: `fusionems-terraform-locks`
   - Point-in-time recovery enabled
   - Used for Terraform state locking to prevent concurrent operations

3. **GitHub OIDC provider**: Configures OpenID Connect federation so GitHub Actions can authenticate without static AWS credentials

4. **IAM deploy role**: `fusionems-github-actions-deploy`
   - Trusts the GitHub OIDC provider scoped to your repository
   - Permissions for ECS, ECR, EC2, RDS, ElastiCache, S3, CloudFront, Route 53, WAF, Cognito, ACM, CloudWatch, Lambda, KMS, Secrets Manager

### Example Output

```
==========================================
  Bootstrap Complete
==========================================

State Buckets:
  - fusionems-terraform-state-dev
  - fusionems-terraform-state-staging
  - fusionems-terraform-state-prod
  - fusionems-terraform-state-dr

Lock Table:       fusionems-terraform-locks
OIDC Provider:    arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com
Deploy Role ARN:  arn:aws:iam::123456789012:role/fusionems-github-actions-deploy
```

---

## GitHub Secrets Configuration

Navigate to **Settings → Secrets and variables → Actions** in your repository.

| Secret                | Required | Description                                          |
|-----------------------|----------|------------------------------------------------------|
| `AWS_ROLE_TO_ASSUME`  | Yes      | IAM role ARN from `bootstrap.sh` output              |
| `INFRACOST_API_KEY`   | No       | Infracost API key for cost estimates on PRs          |

> **Note:** No static AWS access keys are needed. All authentication uses OIDC federation.

---

## Directory Structure

```
infra/terraform/
├── environments/
│   ├── dev/                    # Development environment
│   │   ├── main.tf             # Module composition (root config)
│   │   ├── variables.tf        # Input variable declarations
│   │   ├── outputs.tf          # Output values
│   │   ├── backend.tf          # S3 remote state configuration
│   │   └── terraform.tfvars    # Environment-specific values
│   ├── staging/                # Staging environment (same structure)
│   ├── prod/                   # Production environment (same structure)
│   └── dr/                     # Disaster recovery environment (us-west-2)
│
├── modules/
│   ├── acm/                    # SSL/TLS certificates
│   ├── cognito/                # User authentication pools
│   ├── ecs-cluster/            # ECS cluster, ALB, ECR repos, log groups
│   ├── ecs-service/            # ECS service & task definitions
│   ├── edge/                   # CloudFront distribution + Route 53 records
│   ├── iam/                    # IAM roles & policies
│   ├── networking/             # VPC, subnets, NAT, security groups
│   ├── observability/          # CloudWatch alarms, dashboards, SNS
│   ├── rds/                    # PostgreSQL RDS instance
│   ├── redis/                  # ElastiCache Redis cluster
│   ├── s3/                     # Application S3 buckets
│   ├── ses/                    # Email service (Graph integration)
│   └── waf/                    # Web Application Firewall rules
```

**Modules vs. environments:** Modules are reusable building blocks that define individual AWS services. Each environment directory composes these modules with environment-specific values via `terraform.tfvars`. All environments share identical module code — only the variables differ.

---

## CI/CD Pipeline

### On Pull Request (paths: `infra/terraform/**`)

The following jobs run in parallel where possible:

| Step | Job | Description |
|------|-----|-------------|
| 1 | **lint-and-validate** | `terraform fmt -check -recursive` and `terraform validate` |
| 2 | **security-scan** | tfsec static analysis + checkov compliance scan |
| 3 | **policy-check** | OPA/Conftest policy evaluation against `opa/policies/` |
| 4 | **plan** | `terraform plan` output posted as PR comment |
| 5 | **cost-estimate** | Infracost diff posted as PR comment |
| 6 | **container-scan** | Trivy vulnerability scan on backend Docker image (fails on CRITICAL) |
| 7 | **destructive-change-detection** | Flags RDS/VPC deletions; requires `approve-destroy` label to proceed |

### On Merge to Main

| Step | Job | Description |
|------|-----|-------------|
| 1 | **lint-and-validate** | Format and validation check |
| 2 | **apply** | `terraform apply -auto-approve` against the `production` environment |

The apply job requires the `production` environment approval gate in GitHub.

Authentication uses OIDC — no static AWS credentials are stored anywhere.

### Nightly (3 AM UTC)

| Step | Job | Description |
|------|-----|-------------|
| 1 | **detect-drift** | Runs `terraform plan -detailed-exitcode` against prod |
| 2 | **alert** | Auto-creates a GitHub issue labeled `infrastructure`, `drift` if changes detected |

Can also be triggered manually via **Actions → Terraform Drift Detection → Run workflow**.

---

## Environment Promotion Model

```
dev  →  staging  →  prod
                      ↓
                     dr (us-west-2)
```

Each environment has:
- **Isolated Terraform state** in its own S3 bucket (`fusionems-terraform-state-<env>`)
- **Separate `terraform.tfvars`** with environment-specific sizing and domains
- **Independent VPC CIDR ranges** (dev: `10.0.0.0/16`, staging: `10.1.0.0/16`, prod: `10.2.0.0/16`)

### Promotion Workflow

1. Develop and test changes in `dev`:
   ```bash
   cd infra/terraform/environments/dev
   terraform plan
   terraform apply
   ```

2. Promote to staging by updating `staging/terraform.tfvars` and merging a PR.

3. After staging validation, update `prod/terraform.tfvars` and merge. The CI/CD pipeline applies automatically.

---

## Manual Override Procedure

### Run Terraform Locally

```bash
# Authenticate via OIDC role (or use your own credentials)
export AWS_PROFILE=fusionems-deploy

# Plan against a specific environment
cd infra/terraform/environments/dev
terraform init
terraform plan -out=tfplan

# Apply (requires appropriate IAM permissions)
terraform apply tfplan
```

### Import Existing Resources

```bash
cd infra/terraform/environments/prod
terraform import module.rds.aws_db_instance.main fusionems-prod-db
```

### State Emergencies

```bash
# View current state
terraform state list
terraform state show module.networking.aws_vpc.main

# Remove a resource from state (does NOT delete the resource)
terraform state rm module.redis.aws_elasticache_replication_group.main

# Move a resource in state (after refactoring modules)
terraform state mv module.old_name.aws_instance.main module.new_name.aws_instance.main

# Force unlock (if a lock is stuck after a crash)
terraform force-unlock <LOCK_ID>

# Pull state for inspection
terraform state pull > state_backup.json
```

> **⚠ Always back up state before manual operations:**
> ```bash
> aws s3 cp s3://fusionems-terraform-state-prod/fusionems/prod/terraform.tfstate ./backup.tfstate
> ```

---

## Cost Visibility

### Infracost Integration

Infracost runs automatically on every PR that touches `infra/terraform/` and posts a cost breakdown comment.

**Setup:**
1. Get a free API key at [infracost.io](https://www.infracost.io/)
2. Add it as the `INFRACOST_API_KEY` GitHub Actions secret

**PR comment example:**
```
Monthly cost will increase by $45.20 (12%)

├── module.rds.aws_db_instance.main    +$32.00
├── module.redis.aws_elasticache_*     +$8.20
└── module.ecs_cluster.aws_lb.*        +$5.00
```

### Cost Thresholds

To enforce cost limits, add a step to the workflow:

```yaml
- name: Check Cost Threshold
  run: |
    MONTHLY=$(jq '.totalMonthlyCost | tonumber' /tmp/infracost.json)
    if (( $(echo "$MONTHLY > 5000" | bc -l) )); then
      echo "::error::Monthly cost exceeds $5,000 threshold"
      exit 1
    fi
```

---

## Policy Enforcement

### OPA Policies (`opa/policies/`)

| Policy                  | What It Enforces                                                  |
|-------------------------|-------------------------------------------------------------------|
| `require_tags.rego`     | All created resources must have `Project`, `Environment`, `ManagedBy` tags |
| `prevent_open_sg.rego`  | Security groups cannot allow `0.0.0.0/0` ingress on non-HTTPS ports |
| `prevent_public_db.rego`| Database instances must not be publicly accessible                |

Policies are evaluated via [Conftest](https://www.conftest.dev/) against Terraform plan JSON output during PR checks.

### tfsec Security Scanning

Runs automatically on PRs. Catches common AWS misconfigurations (unencrypted storage, overly permissive IAM, missing logging, etc.). Configured as **hard-fail** — PRs are blocked on findings.

### Checkov Compliance Scanning

Configuration in `checkov.yml`:

```yaml
compact: true
directory: [infra/terraform]
framework: [terraform]
quiet: true
skip-check:
  - CKV_AWS_144   # S3 cross-region replication (handled by DR env)
  - CKV_AWS_145   # S3 KMS encryption (using AES-256)
  - CKV2_AWS_6    # S3 public access (handled by bucket policy)
soft-fail: false
```

### Pre-commit Hooks

Run format checks and validation locally before pushing:

```bash
cd infra/terraform
terraform fmt -check -recursive
terraform validate
```

---

## Security Controls

### Authentication & Access
- **OIDC-only authentication** — no static AWS access keys in CI/CD
- **Cognito user pools** for application authentication
- **Least-privilege IAM** — deploy role scoped to project resources
- **GitHub environment protection** — `production` environment requires approval

### Network Security
- **WAF** on ALB and CloudFront (rate limiting, managed rule groups)
- **Private subnets** for ECS tasks, RDS, and Redis
- **Security groups** restrict traffic between tiers
- **No public database access** — RDS and Redis in private subnets only
- **NAT Gateway** for outbound internet from private subnets

### Data Protection
- **Encryption at rest** — KMS for RDS, AES-256 for S3, encryption for Redis
- **Encryption in transit** — TLS everywhere (ALB, CloudFront, database connections)
- **Secrets in AWS Secrets Manager** — database URLs, Redis auth, API keys
- **S3 bucket policies** enforce TLS-only access

### Audit & Monitoring
- **CloudTrail** for API audit logging
- **GuardDuty** for threat detection
- **VPC Flow Logs** for network monitoring

---

## Observability

### CloudWatch Alarms

The `observability` module creates alarms for:

| Metric                  | Threshold             | Resource      |
|-------------------------|-----------------------|---------------|
| CPU utilization         | > 80% for 5 min      | ECS services  |
| Memory utilization      | > 80% for 5 min      | ECS services  |
| 5xx error rate          | > 5% for 5 min       | ALB           |
| Target response time    | > 2s p99 for 5 min   | ALB           |
| DB connections          | > 80% max for 5 min  | RDS           |
| DB free storage         | < 5 GB                | RDS           |
| Redis CPU               | > 80% for 5 min      | ElastiCache   |
| Redis memory            | > 80% for 5 min      | ElastiCache   |

### Alerting

All alarms publish to an SNS topic. Configure the `alert_email` variable in `terraform.tfvars`:

```hcl
alert_email = "alerts@fusionems.com"
```

### Local Development Observability

The `docker-compose.yml` provides a full observability stack:

| Service           | Port  | Purpose                          |
|-------------------|-------|----------------------------------|
| Prometheus        | 9090  | Metrics collection (15s scrape)  |
| Grafana           | 3001  | Dashboards and visualization     |
| OTEL Collector    | 4318  | Trace and metric ingestion       |

Access Grafana at `http://localhost:3001` (Prometheus datasource pre-configured).

### Production Observability

- CloudWatch dashboards for ECS, RDS, Redis, and ALB metrics
- CloudWatch Logs for ECS container logs
- Integration points for external Prometheus/Grafana via OTEL Collector

---

## Disaster Recovery

### DR Environment

A dedicated DR environment in `us-west-2` mirrors production infrastructure:

```
infra/terraform/environments/dr/
├── main.tf
├── variables.tf
├── outputs.tf
├── backend.tf          # State in fusionems-terraform-state-dr
└── terraform.tfvars    # DR-specific configuration
```

### Key Properties

- **Separate AWS region** (`us-west-2`) from production (`us-east-1`)
- **Independent Terraform state** in `fusionems-terraform-state-dr`
- **Isolated VPC and networking** — no cross-region dependencies
- **DNS failover** via Route 53 health checks and weighted routing

### Failover Procedure

1. Verify DR environment is healthy:
   ```bash
   cd infra/terraform/environments/dr
   terraform plan    # should show no changes
   ```

2. Update Route 53 to point to DR:
   ```bash
   # Update DNS weights or trigger health-check-based failover
   aws route53 change-resource-record-sets --hosted-zone-id <ZONE_ID> \
     --change-batch file://failover-changeset.json
   ```

3. Validate:
   ```bash
   curl -s https://api.fusionems.com/api/v1/health
   ```

---

## Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| `Error: No valid credential sources found` | OIDC not configured | Run `bootstrap.sh` or check `AWS_ROLE_TO_ASSUME` secret |
| `Error: Error acquiring the state lock` | Previous run crashed | `terraform force-unlock <LOCK_ID>` |
| `Error: Backend configuration changed` | State bucket mismatch | Run `terraform init -reconfigure` |
| PR blocked with "DESTRUCTIVE CHANGES" | Plan deletes RDS or VPC | Add `approve-destroy` label to the PR after review |
| Drift detection issue created | Manual changes in console | Run `terraform apply` to reconcile, or import the change |
| Infracost comment missing | API key not set | Add `INFRACOST_API_KEY` secret (optional) |

### Check Terraform State

```bash
# List all resources in state
cd infra/terraform/environments/prod
terraform state list

# Show details of a specific resource
terraform state show module.rds.aws_db_instance.main

# Verify state matches reality
terraform plan
```

### View ECS Logs

```bash
# Stream backend logs
aws logs tail /ecs/fusionems-prod --follow --filter-pattern "ERROR"

# Get recent log events
aws logs get-log-events \
  --log-group-name /ecs/fusionems-prod \
  --log-stream-name "backend/backend/<task-id>" \
  --limit 100

# Describe running tasks
aws ecs list-tasks --cluster fusionems-prod --service-name fusionems-prod-backend
aws ecs describe-tasks --cluster fusionems-prod --tasks <task-arn>
```

### Rollback

**Terraform rollback** (revert to previous configuration):

```bash
# Option 1: Revert the git commit and let CI/CD re-apply
git revert <commit-sha>
git push origin main

# Option 2: Manually apply a previous version
git checkout <previous-sha> -- infra/terraform/
cd infra/terraform/environments/prod
terraform init
terraform apply
```

**ECS service rollback** (revert to previous container image):

```bash
# Find previous task definition
aws ecs describe-services --cluster fusionems-prod \
  --services fusionems-prod-backend \
  --query 'services[0].taskDefinition'

# Update to a previous task definition revision
aws ecs update-service --cluster fusionems-prod \
  --service fusionems-prod-backend \
  --task-definition fusionems-prod-backend:<previous-revision>

# Or use the helper script
python scripts/ecs_update_service.py \
  --cluster fusionems-prod \
  --service fusionems-prod-backend \
  --region us-east-1
```

### Health Check

```bash
curl -s https://api.fusionems.com/api/v1/health
# Expected: HTTP 200
```
