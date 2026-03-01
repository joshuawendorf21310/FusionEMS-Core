# FusionEMS-Core Deployment (GitHub → AWS CloudFormation)

## Prereqs
- AWS account + Route53 hosted zone for your domain
- ACM certificate in **us-east-1** covering `DomainName` (CloudFront requirement)
- GitHub Actions OIDC role created in AWS (trusts your repo)

## Deploy
1. Set GitHub repository variables/secrets:
   - AWS_REGION
   - AWS_ROLE_TO_ASSUME
   - CFN_STACK_NAME (e.g. fusionems-core-dev)
   - CFN_ENV (dev|prod)
   - CFN_DOMAIN_NAME (e.g. api.example.com)
   - CFN_HOSTED_ZONE_ID
   - CFN_ACM_CERT_ARN_US_EAST_1
   - CFN_DESIRED_COUNT (optional, defaults to 2 tasks if unset)

2. Push to `main`. The workflow builds/pushes the Docker image and deploys `infra/cloudformation/root.yml`.

## Health
- `GET https://<domain>/api/v1/health` should return 200.
