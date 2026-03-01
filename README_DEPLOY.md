# FusionEMS-Core Deployment (GitHub → AWS CloudFormation)

## Prereqs
- AWS account + Route53 hosted zone for your domain
- ACM certificate in **us-east-1** covering `DomainName` (CloudFront requirement)
- GitHub Actions OIDC role created in AWS (trusts your repo)

## Deploy
1. Set GitHub repository variables/secrets:
   - AWS_REGION (defaults to us-east-1)
   - AWS_ROLE_TO_ASSUME (OIDC role ARN)
   - CFN_STACK_NAME (e.g. fusionems-core-dev)
   - CFN_ENV (dev|prod)
   - CFN_ROOT_DOMAIN_NAME (defaults to app.fusionemsquantum.com)
   - CFN_API_DOMAIN_NAME (defaults to api.fusionemsquantum.com, falls back to CFN_DOMAIN_NAME)
   - CFN_DOMAIN_NAME (legacy alias for CFN_API_DOMAIN_NAME)
   - CFN_HOSTED_ZONE_ID
   - CFN_ACM_CERT_ARN_US_EAST_1
   - CFN_ARTIFACT_BUCKET (defaults to fusionemsquantum-cfn-artifacts-prod)
   - IMAGE_TAG_FRONTEND (defaults to latest)
   - IMAGE_TAG_BACKEND (defaults to latest)

2. Push to `main`. The workflow builds/pushes the Docker image and deploys `infra/cloudformation/root.yml`.

## Health
- `GET https://<domain>/api/v1/health` should return 200.
