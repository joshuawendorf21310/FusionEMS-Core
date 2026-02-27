"""Scan source files for placeholder secrets that must not reach production."""
from __future__ import annotations
import re
import sys
from pathlib import Path

PLACEHOLDER_PATTERNS = [
    re.compile(r"REPLACE_WITH_", re.IGNORECASE),
    re.compile(r"YOUR_SECRET_HERE", re.IGNORECASE),
    re.compile(r"<YOUR_", re.IGNORECASE),
    re.compile(r"CHANGE_ME", re.IGNORECASE),
    re.compile(r"TODO_SECRET", re.IGNORECASE),
    re.compile(r"INSERT_API_KEY", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".next", ".mypy_cache", "dist", "build", "venv", ".venv", ".github"}
EXCLUDE_FILES = {"scan_placeholders.py", "release-gate.yml"}
SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".env.example"}

repo_root = Path(__file__).parent.parent


def scan() -> list[str]:
    hits: list[str] = []
    for path in repo_root.rglob("*"):
        if any(ex in path.parts for ex in EXCLUDE_DIRS):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        if path.suffix not in SCAN_EXTENSIONS:
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat in PLACEHOLDER_PATTERNS:
                if pat.search(line):
                    hits.append(f"{path.relative_to(repo_root)}:{lineno}: {line.strip()[:120]}")
                    break
    return hits


if __name__ == "__main__":
    hits = scan()
    if hits:
        print(f"FAIL — {len(hits)} placeholder(s) found:")
        for h in hits:
            print(f"  {h}")
        sys.exit(1)
    print("OK — no placeholders found")
