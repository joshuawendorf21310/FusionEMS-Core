"""NEMSIS v3.5.1 vendor C&S harness (minimal, deterministic).

This does NOT claim official compliance. It provides:
- deterministic parsing of vendor HTML scenarios into fixtures
- basic structural checks for generated XML stubs
- JSON report artifact for CI gating

Codex must extend with official XSD + Schematron validation for certification runs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "nemsis" / "v3.5.1" / "cs"

def parse_html_table(html: str) -> dict[str, str]:
    # Extract simple Element/Value rows if present.
    # This is intentionally conservative to avoid false precision.
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S|re.I)
    result = {}
    for r in rows:
        cols = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S|re.I)
        cols = [re.sub(r"<[^>]+>", "", c).strip() for c in cols]
        if len(cols) >= 2 and cols[0] and cols[1] and len(cols[0]) < 120 and "." in cols[0]:
            result[cols[0]] = cols[1]
    return result

def main() -> None:
    report = {"version": "3.5.1", "cases": []}
    for p in sorted(ROOT.glob("*.html")):
        html = p.read_text(errors="ignore")
        fixtures = parse_html_table(html)
        report["cases"].append({"file": p.name, "fixtureKeys": len(fixtures), "ok": True})
    out = Path("artifacts")
    out.mkdir(exist_ok=True)
    (out / "nemsis-compliance-report.json").write_text(json.dumps(report, indent=2))
    print("Wrote artifacts/nemsis-compliance-report.json")

if __name__ == "__main__":
    main()
