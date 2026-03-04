#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Bootstrap the GitHubTerraformRole IAM role and OIDC provider in AWS
# account 793439286972 for GitHub Actions OIDC authentication.
#
# Prerequisites:
#   - AWS CLI configured with credentials for account 793439286972
#   - jq installed
#
# Usage:
#   ./bootstrap-oidc-role.sh
# ---------------------------------------------------------------------------
set -euo pipefail

ACCOUNT_ID="793439286972"
ROLE_NAME="FusionEMS-GHA-TerraformProd"
OIDC_URL="https://token.actions.githubusercontent.com"
OIDC_CLIENT="sts.amazonaws.com"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRUST_POLICY_FILE="${SCRIPT_DIR}/trust-policy.json"

echo "==> Verifying AWS account..."
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [[ "$CURRENT_ACCOUNT" != "$ACCOUNT_ID" ]]; then
  echo "ERROR: Expected account ${ACCOUNT_ID}, got ${CURRENT_ACCOUNT}" >&2
  exit 1
fi
echo "    Account: ${CURRENT_ACCOUNT}"

# --- OIDC provider ---
echo "==> Checking OIDC provider..."
OIDC_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

EXISTING=$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[?ends_with(Arn, '/token.actions.githubusercontent.com')].Arn" \
  --output text 2>/dev/null || true)

if [[ -n "$EXISTING" && "$EXISTING" != "None" ]]; then
  echo "    OIDC provider exists: ${EXISTING}"
  # Ensure sts.amazonaws.com is in the client ID list
  CLIENTS=$(aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$EXISTING" \
    --query "ClientIDList" --output text 2>/dev/null || true)
  if ! echo "$CLIENTS" | grep -q "sts.amazonaws.com"; then
    echo "    Adding client ID sts.amazonaws.com..."
    aws iam add-client-id-to-open-id-connect-provider \
      --open-id-connect-provider-arn "$EXISTING" \
      --client-id "sts.amazonaws.com"
  fi
else
  echo "    Creating OIDC provider..."
  # AWS requires a SHA-1 thumbprint for OIDC providers (as of 2025).
  THUMBPRINT=$(openssl s_client -servername token.actions.githubusercontent.com \
    -showcerts -connect token.actions.githubusercontent.com:443 </dev/null 2>/dev/null \
    | openssl x509 -fingerprint -sha1 -noout 2>/dev/null \
    | sed 's/[Ss][Hh][Aa]1 Fingerprint=//;s/://g' \
    | tr '[:upper:]' '[:lower:]')

  if [[ -z "$THUMBPRINT" ]]; then
    echo "ERROR: Failed to retrieve GitHub OIDC thumbprint" >&2
    exit 1
  fi

  aws iam create-open-id-connect-provider \
    --url "$OIDC_URL" \
    --client-id-list "$OIDC_CLIENT" \
    --thumbprint-list "$THUMBPRINT" >/dev/null
  echo "    Created OIDC provider: ${OIDC_ARN}"
fi

# --- IAM role ---
echo "==> Checking IAM role ${ROLE_NAME}..."

if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
  ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query "Role.Arn" --output text)
  echo "    Role exists: ${ROLE_ARN}"
  echo "    Updating trust policy..."
  aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document "file://${TRUST_POLICY_FILE}"
else
  echo "    Creating role..."
  ROLE_ARN=$(aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://${TRUST_POLICY_FILE}" \
    --description "GitHub Actions Terraform role for FusionEMS-Core (OIDC)" \
    --query "Role.Arn" \
    --output text)
  echo "    Created role: ${ROLE_ARN}"
fi

echo ""
echo "==> Done."
echo "    Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "    The terraform.yml workflow references this ARN directly."
echo "    No GitHub secret is required for the role ARN."
