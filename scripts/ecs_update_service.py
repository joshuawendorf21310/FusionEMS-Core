"""Update an ECS service, waiting for it to be ACTIVE first.

Usage:
    python scripts/ecs_update_service.py \\
        --cluster <cluster-name> \\
        --service <service-name> \\
        --desired-count <n> \\
        --region <aws-region>

Exits 0 on success, non-zero on failure.
"""
from __future__ import annotations

import argparse
import sys
import time

import boto3
from botocore.exceptions import ClientError


def wait_for_active(ecs: "botocore.client.ECS", cluster: str, service: str, timeout: int = 300) -> None:  # type: ignore[name-defined]
    """Poll until the ECS service status is ACTIVE or timeout expires."""
    deadline = time.monotonic() + timeout
    delay = 10
    while True:
        try:
            resp = ecs.describe_services(cluster=cluster, services=[service])
        except ClientError as exc:
            print(f"  describe_services error: {exc} — waiting {delay}s …", flush=True)
        else:
            svcs = resp.get("services", [])
            if svcs:
                status = svcs[0].get("status", "")
                if status == "ACTIVE":
                    return
                print(f"  Service status is {status!r} — waiting {delay}s …", flush=True)
            else:
                print(f"  Service {service!r} not yet visible — waiting {delay}s …", flush=True)
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Service {service!r} did not reach ACTIVE within {timeout}s"
            )
        time.sleep(delay)


def update_service(
    cluster: str, service: str, region: str, desired_count: int | None = None
) -> None:
    ecs = boto3.client("ecs", region_name=region)

    print(f"Checking status of ECS service {service!r} in cluster {cluster!r} …", flush=True)
    wait_for_active(ecs, cluster, service)

    kwargs: dict = {
        "cluster": cluster,
        "service": service,
        "forceNewDeployment": True,
    }
    if desired_count is not None:
        kwargs["desiredCount"] = desired_count
        msg = f"Service is ACTIVE — updating desired count to {desired_count} with force-new-deployment …"
    else:
        msg = "Service is ACTIVE — triggering force-new-deployment …"
    print(msg, flush=True)

    ecs.update_service(**kwargs)
    print(f"update_service succeeded for {service!r}.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update an ECS service safely.")
    parser.add_argument("--cluster", required=True, help="ECS cluster name or ARN")
    parser.add_argument("--service", required=True, help="ECS service name or ARN")
    parser.add_argument("--desired-count", type=int, default=None, help="Desired task count (optional)")
    parser.add_argument("--region", required=True, help="AWS region")
    args = parser.parse_args()

    try:
        update_service(args.cluster, args.service, args.region, args.desired_count)
    except (ClientError, TimeoutError) as exc:
        print(f"::error::{exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
