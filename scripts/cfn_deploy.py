"""Package and deploy a CloudFormation stack via the boto3 CloudFormation client.

Packages nested templates to S3 using the AWS CLI, then deploys the stack
using boto3 change-set semantics.  An empty change set is treated as a
no-op (equivalent to --no-fail-on-empty-changeset).

Usage:
    python scripts/cfn_deploy.py \\
        --template-file infra/cloudformation/root.yml \\
        --stack-name fusionems-core \\
        --s3-bucket my-artifacts-bucket \\
        --region us-east-1 \\
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \\
        --parameter-overrides Env=prod Key2=Val2

Exits 0 on success, non-zero on failure.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

_NO_CHANGES_REASONS = (
    "The submitted information didn't contain changes",
    "No updates are to be performed",
)


def package_template(template_file: str, s3_bucket: str, output_file: str) -> None:
    """Upload nested templates to S3 and write the packaged template file."""
    cmd = [
        "aws", "cloudformation", "package",
        "--template-file", template_file,
        "--s3-bucket", s3_bucket,
        "--output-template-file", output_file,
    ]
    print(f"Packaging template to s3://{s3_bucket} …", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout, flush=True)
        print(result.stderr, file=sys.stderr, flush=True)
        raise RuntimeError(f"aws cloudformation package failed (exit {result.returncode})")
    print("Template packaged successfully.", flush=True)


def parse_parameter_overrides(overrides: list[str]) -> list[dict]:
    """Convert 'Key=Value' strings to CloudFormation Parameter dicts."""
    params: list[dict] = []
    for item in overrides:
        if "=" not in item:
            raise ValueError(f"Invalid parameter override {item!r} — expected Key=Value format")
        key, _, value = item.partition("=")
        params.append({"ParameterKey": key, "ParameterValue": value})
    return params


def deploy_stack(
    cfn: Any,
    stack_name: str,
    template_body: str,
    parameters: list[dict],
    capabilities: list[str],
    *,
    poll_interval: int = 10,
    timeout: int = 5400,
) -> None:
    """Create or update a CloudFormation stack using a change set."""
    # Determine whether this is a CREATE or UPDATE.
    try:
        resp = cfn.describe_stacks(StackName=stack_name)
        stack_status = resp["Stacks"][0]["StackStatus"]
        change_set_type = "UPDATE"
        print(
            f"Stack {stack_name!r} exists (status {stack_status!r}) "
            "— creating UPDATE change set.",
            flush=True,
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        msg = exc.response.get("Error", {}).get("Message", "")
        if code == "ValidationError" and "does not exist" in msg:
            change_set_type = "CREATE"
            print(f"Stack {stack_name!r} does not exist — creating CREATE change set.", flush=True)
        else:
            raise

    change_set_name = f"deploy-{int(time.time())}"
    cfn.create_change_set(
        StackName=stack_name,
        TemplateBody=template_body,
        Parameters=parameters,
        Capabilities=capabilities,
        ChangeSetName=change_set_name,
        ChangeSetType=change_set_type,
    )

    # Poll until the change set reaches a terminal state.
    print(f"Waiting for change set {change_set_name!r} …", flush=True)
    deadline = time.monotonic() + timeout
    while True:
        cs = cfn.describe_change_set(ChangeSetName=change_set_name, StackName=stack_name)
        status = cs["Status"]
        reason = cs.get("StatusReason", "")

        if status == "CREATE_COMPLETE":
            break

        if status == "FAILED":
            if any(msg in reason for msg in _NO_CHANGES_REASONS):
                print("No changes detected — nothing to deploy.", flush=True)
                cfn.delete_change_set(ChangeSetName=change_set_name, StackName=stack_name)
                return
            raise RuntimeError(f"Change set creation failed: {reason}")

        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Change set {change_set_name!r} timed out in status {status!r}"
            )

        print(f"  Change set status: {status!r} — waiting {poll_interval}s …", flush=True)
        time.sleep(poll_interval)

    changes = cs.get("Changes", [])
    if not changes:
        print("Change set is empty — nothing to deploy.", flush=True)
        cfn.delete_change_set(ChangeSetName=change_set_name, StackName=stack_name)
        return

    print(f"Executing change set ({len(changes)} change(s)) …", flush=True)
    cfn.execute_change_set(ChangeSetName=change_set_name, StackName=stack_name)

    print("Waiting for stack deployment to complete …", flush=True)
    waiter_name = (
        "stack_create_complete" if change_set_type == "CREATE" else "stack_update_complete"
    )
    cfn.get_waiter(waiter_name).wait(
        StackName=stack_name,
        WaiterConfig={"Delay": 30, "MaxAttempts": 180},
    )
    print(f"Stack {stack_name!r} deployed successfully.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package and deploy a CloudFormation stack via the boto3 client."
    )
    parser.add_argument("--template-file", required=True, help="Path to the root CloudFormation template")
    parser.add_argument("--stack-name", required=True, help="CloudFormation stack name")
    parser.add_argument("--s3-bucket", required=True, help="S3 bucket for packaged artifacts")
    parser.add_argument("--region", required=True, help="AWS region")
    parser.add_argument(
        "--capabilities",
        nargs="*",
        default=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        help="IAM capabilities to grant (space-separated)",
    )
    parser.add_argument(
        "--parameter-overrides",
        nargs="*",
        default=[],
        metavar="KEY=VALUE",
        help="CloudFormation parameter overrides in Key=Value format",
    )
    args = parser.parse_args()

    template_path = Path(args.template_file)
    if not template_path.exists():
        print(f"::error::Template file not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    packaged_file = "packaged-root.yml"

    try:
        package_template(str(template_path), args.s3_bucket, packaged_file)
    except RuntimeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)

    template_body = Path(packaged_file).read_text(encoding="utf-8")

    try:
        parameters = parse_parameter_overrides(args.parameter_overrides)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)

    cfn = boto3.client("cloudformation", region_name=args.region)

    try:
        deploy_stack(
            cfn,
            args.stack_name,
            template_body,
            parameters,
            args.capabilities,
        )
    except (ClientError, TimeoutError, RuntimeError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
