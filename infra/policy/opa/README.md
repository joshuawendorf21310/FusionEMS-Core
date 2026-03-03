# OPA Terraform Policy Pack

Conftest-compatible policy pack for Terraform plan validation.

## Policies

### deny_destructive.rego

Blocks all destructive Terraform actions (delete, replace) by default. This is a safety net to prevent accidental infrastructure destruction.

**Default behavior:** Any `delete` or `delete+create` (replace) action is blocked.

### Adding Allow Rules

To allow destruction for specific resources, add patterns to the `explicitly_allowed` rule:

```rego
explicitly_allowed(rc) {
  startswith(rc.address, "module.sandbox.")
}

explicitly_allowed(rc) {
  contains(rc.address, "preview")
}
```

### Override via CI

For legitimate destructive changes:

1. Add the `approve-destroy` label to the Pull Request
2. Request review from the `prod` environment required reviewers
3. The CI pipeline will check for the label before allowing destructive plans

### GitHub Environment Approval for Destructive Overrides

Configure the `prod` environment in GitHub Settings > Environments:
- Add required reviewers (minimum 1 founder/admin)
- Enable deployment branch protection (main only)
- The `apply_prod` job requires this environment approval before execution

### Running Locally

```bash
cd infra/terraform/environments/prod
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
conftest test tfplan.json -p ../../policy/opa
```
