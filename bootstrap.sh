#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Configurable variables
# ---------------------------------------------------------------------------
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT="${PROJECT:-fusionems}"
GITHUB_ORG="${GITHUB_ORG:-}"
GITHUB_REPO="${GITHUB_REPO:-}"
STATE_BUCKET_PREFIX="${STATE_BUCKET_PREFIX:-fusionems-terraform-state}"
LOCK_TABLE="${LOCK_TABLE:-fusionems-terraform-locks}"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
skip()    { printf "${YELLOW}[SKIP]${NC}  %s\n" "$*"; }
err()     { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) AWS_REGION="$2"; shift 2 ;;
    --org)    GITHUB_ORG="$2"; shift 2 ;;
    --repo)   GITHUB_REPO="$2"; shift 2 ;;
    *)        err "Unknown argument: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validate required variables
# ---------------------------------------------------------------------------
if [[ -z "$GITHUB_ORG" ]]; then
  err "GITHUB_ORG must be set via environment variable or --org flag"
  exit 1
fi
if [[ -z "$GITHUB_REPO" ]]; then
  err "GITHUB_REPO must be set via environment variable or --repo flag"
  exit 1
fi

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
info "Checking prerequisites..."

if ! command -v aws &>/dev/null; then
  err "aws CLI is not installed. Please install it first."
  exit 1
fi

if ! aws sts get-caller-identity &>/dev/null; then
  err "aws CLI is not configured or credentials are invalid."
  exit 1
fi

if ! command -v jq &>/dev/null; then
  err "jq is not installed. Please install it first."
  exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
success "AWS account: ${ACCOUNT_ID}, region: ${AWS_REGION}"

# ---------------------------------------------------------------------------
# 1. Create S3 state buckets per environment
# ---------------------------------------------------------------------------
ENVIRONMENTS=(dev staging prod dr)

for env in "${ENVIRONMENTS[@]}"; do
  BUCKET="${STATE_BUCKET_PREFIX}-${env}"
  info "Processing S3 bucket: ${BUCKET}"

  if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
    skip "Bucket ${BUCKET} already exists"
  else
    # Create bucket (us-east-1 must not specify LocationConstraint)
    if [[ "$AWS_REGION" == "us-east-1" ]]; then
      aws s3api create-bucket \
        --bucket "$BUCKET" \
        --region "$AWS_REGION" >/dev/null
    else
      aws s3api create-bucket \
        --bucket "$BUCKET" \
        --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
    fi
    success "Created bucket ${BUCKET}"
  fi

  # Enable versioning
  aws s3api put-bucket-versioning \
    --bucket "$BUCKET" \
    --versioning-configuration Status=Enabled >/dev/null
  success "Versioning enabled on ${BUCKET}"

  # Block all public access
  aws s3api put-public-access-block \
    --bucket "$BUCKET" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true >/dev/null
  success "Public access blocked on ${BUCKET}"

  # Default AES256 encryption
  aws s3api put-bucket-encryption \
    --bucket "$BUCKET" \
    --server-side-encryption-configuration \
      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},"BucketKeyEnabled":true}]}' >/dev/null
  success "AES256 encryption enabled on ${BUCKET}"

  # TLS-only bucket policy
  POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceTLS",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
EOF
)
  aws s3api put-bucket-policy --bucket "$BUCKET" --policy "$POLICY" >/dev/null
  success "TLS policy applied to ${BUCKET}"
done

# ---------------------------------------------------------------------------
# 2. Create DynamoDB lock table
# ---------------------------------------------------------------------------
info "Processing DynamoDB table: ${LOCK_TABLE}"

if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$AWS_REGION" &>/dev/null; then
  skip "DynamoDB table ${LOCK_TABLE} already exists"
else
  aws dynamodb create-table \
    --table-name "$LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION" >/dev/null

  info "Waiting for table ${LOCK_TABLE} to become active..."
  aws dynamodb wait table-exists --table-name "$LOCK_TABLE" --region "$AWS_REGION"
  success "Created DynamoDB table ${LOCK_TABLE}"
fi

# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name "$LOCK_TABLE" \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --region "$AWS_REGION" >/dev/null
success "Point-in-time recovery enabled on ${LOCK_TABLE}"

# ---------------------------------------------------------------------------
# 3. Create GitHub OIDC provider
# ---------------------------------------------------------------------------
OIDC_URL="https://token.actions.githubusercontent.com"
OIDC_CLIENT="sts.amazonaws.com"

info "Processing GitHub OIDC provider"

EXISTING_OIDC=$(aws iam list-open-id-connect-providers --query \
  "OpenIDConnectProviderList[?ends_with(Arn, '/token.actions.githubusercontent.com')].Arn" \
  --output text 2>/dev/null || true)

if [[ -n "$EXISTING_OIDC" && "$EXISTING_OIDC" != "None" ]]; then
  OIDC_ARN="$EXISTING_OIDC"
  skip "OIDC provider already exists: ${OIDC_ARN}"
else
  # Fetch current GitHub Actions OIDC thumbprint
  THUMBPRINT=$(openssl s_client -servername token.actions.githubusercontent.com \
    -showcerts -connect token.actions.githubusercontent.com:443 </dev/null 2>/dev/null \
    | openssl x509 -fingerprint -sha1 -noout 2>/dev/null \
    | sed 's/sha1 Fingerprint=//;s/://g' \
    | tr '[:upper:]' '[:lower:]')

  if [[ -z "$THUMBPRINT" ]]; then
    err "Failed to retrieve GitHub OIDC thumbprint"
    exit 1
  fi

  OIDC_ARN=$(aws iam create-open-id-connect-provider \
    --url "$OIDC_URL" \
    --client-id-list "$OIDC_CLIENT" \
    --thumbprint-list "$THUMBPRINT" \
    --query "OpenIDConnectProviderArn" \
    --output text)
  success "Created OIDC provider: ${OIDC_ARN}"
fi

# ---------------------------------------------------------------------------
# 4. Create IAM role for GitHub Actions
# ---------------------------------------------------------------------------
ROLE_NAME="${PROJECT}-github-actions-deploy"

info "Processing IAM role: ${ROLE_NAME}"

TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${OIDC_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        },
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF
)

INLINE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSAndECR",
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ecr:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2Networking",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "ec2:CreateVpc",
        "ec2:DeleteVpc",
        "ec2:*Subnet*",
        "ec2:*SecurityGroup*",
        "ec2:*Route*",
        "ec2:*InternetGateway*",
        "ec2:*NatGateway*",
        "ec2:*VpcEndpoint*",
        "ec2:*NetworkAcl*",
        "ec2:AllocateAddress",
        "ec2:ReleaseAddress",
        "ec2:*FlowLog*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DataStores",
      "Effect": "Allow",
      "Action": [
        "rds:*",
        "elasticache:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "StorageAndCDN",
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "cloudfront:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DNSAndSecurity",
      "Effect": "Allow",
      "Action": [
        "route53:*",
        "wafv2:*",
        "cognito-idp:*",
        "acm:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Observability",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:*",
        "logs:*",
        "sns:*",
        "sqs:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMScoped",
      "Effect": "Allow",
      "Action": "iam:*",
      "Resource": "arn:aws:iam::${ACCOUNT_ID}:*/${PROJECT}*"
    },
    {
      "Sid": "SecurityServices",
      "Effect": "Allow",
      "Action": [
        "kms:*",
        "secretsmanager:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Compute",
      "Effect": "Allow",
      "Action": "lambda:*",
      "Resource": "*"
    },
    {
      "Sid": "StateLocking",
      "Effect": "Allow",
      "Action": "dynamodb:*",
      "Resource": "*"
    },
    {
      "Sid": "Identity",
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
EOF
)

if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
  ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query "Role.Arn" --output text)
  skip "IAM role already exists: ${ROLE_ARN}"

  # Update trust policy and inline policy to stay current
  aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document "$TRUST_POLICY" >/dev/null
  success "Updated trust policy on ${ROLE_NAME}"

  aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "${PROJECT}-deploy-permissions" \
    --policy-document "$INLINE_POLICY" >/dev/null
  success "Updated inline policy on ${ROLE_NAME}"
else
  ROLE_ARN=$(aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST_POLICY" \
    --description "GitHub Actions deploy role for ${PROJECT}" \
    --query "Role.Arn" \
    --output text)
  success "Created IAM role: ${ROLE_ARN}"

  aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "${PROJECT}-deploy-permissions" \
    --policy-document "$INLINE_POLICY" >/dev/null
  success "Attached inline policy to ${ROLE_NAME}"
fi

# ---------------------------------------------------------------------------
# 5. Summary
# ---------------------------------------------------------------------------
echo ""
printf "${GREEN}==========================================${NC}\n"
printf "${GREEN}  Bootstrap Complete${NC}\n"
printf "${GREEN}==========================================${NC}\n"
echo ""
info "State Buckets:"
for env in "${ENVIRONMENTS[@]}"; do
  echo "  - ${STATE_BUCKET_PREFIX}-${env}"
done
echo ""
info "Lock Table:       ${LOCK_TABLE}"
info "OIDC Provider:    ${OIDC_ARN}"
info "Deploy Role ARN:  ${ROLE_ARN}"
echo ""
printf "${CYAN}Next Steps:${NC}\n"
echo "  1. Add the following GitHub Actions secret:"
echo "       AWS_DEPLOY_ROLE_ARN = ${ROLE_ARN}"
echo ""
echo "  2. Configure Terraform backends in each environment to use:"
echo "       bucket         = \"${STATE_BUCKET_PREFIX}-<env>\""
echo "       dynamodb_table = \"${LOCK_TABLE}\""
echo "       region         = \"${AWS_REGION}\""
echo "       encrypt        = true"
echo ""
echo "  3. Use 'aws-actions/configure-aws-credentials' in workflows"
echo "     with role-to-assume pointing to the deploy role ARN."
echo ""
success "Bootstrap finished successfully."
