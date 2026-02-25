# Deployment (AWS CloudFormation) — fusionemsquantum.com

This repo deploys as:
- Landing/UI: `https://fusionemsquantum.com`
- API: `https://api.fusionemsquantum.com`

## Prerequisites (must)
1. Route53 hosted zone for `fusionemsquantum.com` (record its HostedZoneId)
2. ACM Certificate in **us-east-1** covering:
   - `fusionemsquantum.com`
   - `api.fusionemsquantum.com`
   CloudFront requires us-east-1 certificates.
3. An S3 bucket for CloudFormation packaging artifacts (e.g. `fusionems-quantum-cfn-artifacts-prod`)

## GitHub Actions configuration
Create these **Repository Variables**:
- `AWS_REGION` (e.g. `us-east-2`)
- `CFN_STACK_NAME` (e.g. `fusionems-quantum-prod`)
- `CFN_ENV` (`prod`)
- `CFN_ROOT_DOMAIN_NAME` (`fusionemsquantum.com`)
- `CFN_API_DOMAIN_NAME` (`api.fusionemsquantum.com`)
- `CFN_HOSTED_ZONE_ID` (your Route53 zone id)
- `CFN_ACM_CERT_ARN_US_EAST_1` (ACM ARN in us-east-1)
- `CFN_ARTIFACTS_BUCKET` (S3 bucket name for packaging)

Create this **Repository Secret**:
- `AWS_ROLE_TO_ASSUME` — IAM Role ARN with CloudFormation/ECS/ECR permissions and GitHub OIDC trust.

## Local deploy (optional)
You can deploy manually after building/pushing images by running `aws cloudformation package` then `aws cloudformation deploy`.
