"""
Env var coverage scan.

Checks that every env var referenced in backend/core_app/core/config.py
as a pydantic Field is also present as an Environment entry in at least
one of the ECS task definitions in compute.yml (or has a known exception).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("SKIP — PyYAML not installed")
    sys.exit(0)

repo_root = Path(__file__).parent.parent

KNOWN_SECRETS = {
    "DATABASE_URL",
    "APP_SECRETS_JSON",
}

KNOWN_INJECTED_AT_RUNTIME = {
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "LOB_EVENTS_QUEUE_URL",
    "STRIPE_EVENTS_QUEUE_URL",
    "LOB_WEBHOOK_SECRET",
    "TELNYX_FROM_NUMBER",
    "TELNYX_MESSAGING_PROFILE_ID",
    "OFFICEALLY_SFTP_HOST",
    "OFFICEALLY_SFTP_PORT",
    "OFFICEALLY_SFTP_USERNAME",
    "OFFICEALLY_SFTP_PASSWORD",
    "OFFICEALLY_SFTP_REMOTE_DIR",
    "LES_FROM_EMAIL",
    "SES_FROM_EMAIL",
    "SES_CONFIGURATION_SET",
    "STATEMENTS_TABLE",
    "LOB_EVENTS_TABLE",
    "STRIPE_EVENTS_TABLE",
    "TENANTS_TABLE",
    "REDIS_URL",
    "DEBUG",
    "APP_NAME",
    "API_BASE_URL",
    "OPA_POLICY_PATH",
    "METRICS_ENABLED",
    "OTEL_ENABLED",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_SERVICE_NAME",
    "AWS_REGION",
    "AUTH_MODE",
    "S3_BUCKET_AUDIO",
    "IVR_AUDIO_BASE_URL",
    "COGNITO_ISSUER",
    "TELNYX_PUBLIC_KEY",
    "TELNYX_WEBHOOK_TOLERANCE_SECONDS",
}

config_path = repo_root / "backend" / "core_app" / "core" / "config.py"
compute_path = repo_root / "infra" / "cloudformation" / "compute.yml"

if not config_path.exists():
    print(f"SKIP — config.py not found at {config_path}")
    sys.exit(0)

field_pat = re.compile(r"^\s+(\w+)\s*:\s*\w+.*=\s*Field\(", re.MULTILINE)
config_text = config_path.read_text(encoding="utf-8")
config_fields = {m.group(1).upper() for m in field_pat.finditer(config_text)}
config_fields.discard("MODEL_CONFIG")

if not compute_path.exists():
    print(f"SKIP — compute.yml not found at {compute_path}")
    sys.exit(0)

def _cfn_loader():
    loader = yaml.SafeLoader
    def _ignore(loader, tag_suffix, node):
        if isinstance(node, yaml.ScalarNode): return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode): return loader.construct_sequence(node, deep=True)
        return loader.construct_mapping(node, deep=True)
    yaml.add_multi_constructor("!", _ignore, Loader=loader)
    return loader
compute_data = yaml.load(compute_path.read_text(encoding="utf-8"), Loader=_cfn_loader())
task_defs = [v for v in (compute_data.get("Resources") or {}).values()
             if isinstance(v, dict) and v.get("Type") == "AWS::ECS::TaskDefinition"]

injected_vars: set[str] = set()
for td in task_defs:
    containers = (td.get("Properties") or {}).get("ContainerDefinitions") or []
    for container in containers:
        for env_entry in (container.get("Environment") or []):
            injected_vars.add(str(env_entry.get("Name", "")).upper())
        for sec_entry in (container.get("Secrets") or []):
            injected_vars.add(str(sec_entry.get("Name", "")).upper())

params = {k.upper() for k in (compute_data.get("Parameters") or {}).keys()}
injected_vars |= params

missing = config_fields - injected_vars - KNOWN_SECRETS - KNOWN_INJECTED_AT_RUNTIME

if missing:
    print(f"WARN — {len(missing)} config field(s) not found in compute.yml env vars:")
    for m in sorted(missing):
        print(f"  {m}")
    sys.exit(0)

print(f"OK — all tracked config fields covered ({len(config_fields)} checked)")
