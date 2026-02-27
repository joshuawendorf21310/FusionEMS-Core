"""Validate CloudFormation templates for basic structural correctness."""
from __future__ import annotations
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("SKIP — PyYAML not installed")
    sys.exit(0)


def _cfn_loader() -> type:
    loader = yaml.SafeLoader

    def _ignore_tag(loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node) -> object:
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node, deep=True)
        return loader.construct_mapping(node, deep=True)

    yaml.add_multi_constructor("!", _ignore_tag, Loader=loader)
    return loader


REQUIRED_TOP_KEYS = {"AWSTemplateFormatVersion", "Resources"}
VALID_RESOURCE_TYPE_PREFIXES = ("AWS::", "Custom::", "Alexa::")

repo_root = Path(__file__).parent.parent
cfn_dirs = [repo_root / "infra" / "cloudformation", repo_root / "cloudformation"]

loader_cls = _cfn_loader()
failures: list[str] = []

for cfn_dir in cfn_dirs:
    if not cfn_dir.exists():
        continue
    for template_path in sorted(cfn_dir.glob("*.yml")):
        try:
            data = yaml.load(template_path.read_text(encoding="utf-8"), Loader=loader_cls)
        except Exception as exc:
            failures.append(f"{template_path.name}: YAML parse error: {exc}")
            continue

        if not isinstance(data, dict):
            failures.append(f"{template_path.name}: not a YAML mapping")
            continue

        missing_keys = REQUIRED_TOP_KEYS - set(data.keys())
        if missing_keys:
            failures.append(f"{template_path.name}: missing required keys: {sorted(missing_keys)}")
            continue

        resources: dict = data.get("Resources") or {}
        if not resources:
            failures.append(f"{template_path.name}: Resources section is empty")
            continue

        for logical_id, resource in resources.items():
            if not isinstance(resource, dict):
                failures.append(f"{template_path.name}/{logical_id}: resource is not a mapping")
                continue
            rtype = resource.get("Type", "")
            if not any(rtype.startswith(p) for p in VALID_RESOURCE_TYPE_PREFIXES):
                failures.append(f"{template_path.name}/{logical_id}: unrecognised Type: {rtype!r}")

if failures:
    print(f"FAIL — {len(failures)} CloudFormation validation issue(s):")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)

print("OK — all CloudFormation templates valid")
