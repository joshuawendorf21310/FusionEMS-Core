"""Scan for duplicate logical IDs within each CloudFormation template."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    print("SKIP — PyYAML not installed; install with: pip install pyyaml")
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
            print(f"WARN — could not parse {template_path.name}: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        resources: dict = data.get("Resources") or {}
        counts = Counter(resources.keys())
        dups = [k for k, v in counts.items() if v > 1]
        if dups:
            failures.append(f"{template_path.relative_to(repo_root)}: duplicate logical IDs: {dups}")

if failures:
    print(f"FAIL — {len(failures)} duplicate logical ID issue(s):")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)

print("OK — no duplicate CloudFormation logical IDs")
