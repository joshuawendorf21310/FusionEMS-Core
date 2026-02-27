#!/usr/bin/env python3
"""
CI Gate: Route Matrix + Endpoint Coverage + HEMS Realtime
Fails if any P0/P1 blocking condition is detected.

Exit codes:
  0 = all gates pass
  1 = one or more gates failed
"""
from __future__ import annotations

import os
import re
import sys
import json

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend", "app")
BACKEND_API = os.path.join(os.path.dirname(__file__), "..", "backend", "core_app", "api")
BACKEND_BILLING = os.path.join(os.path.dirname(__file__), "..", "backend", "core_app", "billing")

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"OK    {msg}")


# ─── Helper: read all page.tsx files ─────────────────────────────────────────

def iter_pages():
    for root, dirs, files in os.walk(FRONTEND):
        dirs[:] = [d for d in dirs if d not in ["node_modules", ".next", ".git"]]
        for fname in files:
            if fname == "page.tsx":
                fpath = os.path.join(root, fname)
                rel = fpath.replace(FRONTEND, "").replace("/page.tsx", "") or "/"
                with open(fpath, errors="replace") as f:
                    content = f.read()
                yield rel, content


# ─── Helper: collect all backend endpoint full paths ─────────────────────────

def collect_backend_paths() -> set[str]:
    ROUTE_RE = re.compile(r'@router\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)
    PREFIX_RE = re.compile(r'APIRouter\s*\([^)]*prefix\s*=\s*["\']([^"\']+)["\']')

    paths: set[str] = set()
    search_dirs = [BACKEND_API, BACKEND_BILLING]
    for api_dir in search_dirs:
        if not os.path.isdir(api_dir):
            continue
        for root, dirs, files in os.walk(api_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, errors="replace") as f:
                    content = f.read()
                pm = PREFIX_RE.search(content)
                prefix = pm.group(1) if pm else ""
                for m in ROUTE_RE.finditer(content):
                    paths.add(prefix + m.group(2))
    return paths


def norm(p: str) -> str:
    p = re.sub(r"\?.*", "", p)
    p = re.sub(r"\$\{[^}]+\}", "{}", p)
    p = re.sub(r"\{[^}]+\}", "{}", p)
    return p.rstrip("/")


# ─── Gate 1: Known-broken path mismatches ────────────────────────────────────

KNOWN_MISMATCHES = [
    (
        "/founder/comms/inbox",
        re.compile(r"/api/v1/support/founder/"),
        "page calls /api/v1/support/founder/... but backend is /api/v1/support/inbox/...",
    ),
    (
        "/portal/rep/",
        re.compile(r"/api/v1/auth-rep/otp/request"),
        "page calls /auth-rep/otp/request — backend is /auth-rep/register",
    ),
    (
        "/portal/rep/",
        re.compile(r"/api/v1/auth-rep/otp/verify"),
        "page calls /auth-rep/otp/verify — backend is /auth-rep/verify-otp",
    ),
]


def gate_known_mismatches() -> None:
    for route, pattern, reason in KNOWN_MISMATCHES:
        for rel, content in iter_pages():
            if route not in rel:
                continue
            if pattern.search(content):
                fail(f"PATH-MISMATCH [{rel}]: {reason}")
                return
    ok("No known path mismatches detected")


# ─── Gate 2: Required endpoints exist in backend ─────────────────────────────

REQUIRED_ENDPOINTS = [
    "/api/v1/hems/checklist-template",
    "/api/v1/hems/missions/{}/acceptance",
    "/api/v1/hems/missions/{}/weather-brief",
    "/api/v1/hems/aircraft/{}/readiness",
    "/api/v1/hems/missions/{}/safety-timeline",
    "/api/v1/support/inbox",
    "/api/v1/support/inbox/{}/reply",
    "/api/v1/support/inbox/{}/resolve",
    "/api/v1/edi/batches",
    "/api/v1/edi/batches/generate",
    "/api/v1/auth-rep/register",
    "/api/v1/auth-rep/verify-otp",
    "/api/v1/billing-command/dashboard",
    "/api/v1/roi-funnel/roi-estimate",
    "/api/v1/system-health/services",
]


def gate_required_endpoints() -> None:
    paths = collect_backend_paths()
    known_norm = {norm(p) for p in paths}
    for ep in REQUIRED_ENDPOINTS:
        if norm(ep) not in known_norm:
            fail(f"MISSING-ENDPOINT: {ep} not found in any backend router")
        else:
            ok(f"endpoint exists: {ep}")


# ─── Gate 3: HEMS page has no silent catches ─────────────────────────────────

HEMS_PAGE = os.path.join(FRONTEND, "portal", "hems", "page.tsx")
SILENT_CATCH_RE = re.compile(r"\.catch\s*\(\s*\(\s*\)\s*=>\s*\{?\s*\}?\s*\)", re.MULTILINE)


def gate_hems_no_silent_catches() -> None:
    if not os.path.exists(HEMS_PAGE):
        fail("HEMS-PAGE-MISSING: portal/hems/page.tsx not found")
        return
    with open(HEMS_PAGE, errors="replace") as f:
        content = f.read()
    matches = SILENT_CATCH_RE.findall(content)
    if matches:
        fail(f"HEMS-SILENT-CATCH: {len(matches)} silent .catch()=>{{}} in portal/hems/page.tsx")
    else:
        ok("HEMS page has no silent catches")


# ─── Gate 4: HEMS backend endpoints not bare stubs ──────────────────────────

HEMS_ROUTER = os.path.join(BACKEND_API, "hems_router.py")
BARE_PASS_RE = re.compile(r"^\s*pass\s*$", re.MULTILINE)


def gate_hems_not_stub() -> None:
    if not os.path.exists(HEMS_ROUTER):
        fail("HEMS-ROUTER-MISSING: backend/core_app/api/hems_router.py not found")
        return
    with open(HEMS_ROUTER, errors="replace") as f:
        content = f.read()
    if BARE_PASS_RE.search(content):
        fail("HEMS-ROUTER-STUB: hems_router.py contains bare `pass` statement")
    else:
        ok("HEMS router has no bare stubs")


# ─── Gate 5: No hardcoded fake-data labels in shipped pages ──────────────────

FAKE_LABEL_RE = re.compile(
    r'"(Coming soon|Under construction|Placeholder|Not implemented|mock data|demo data|sample data|fake data)"',
    re.IGNORECASE,
)


def gate_no_fake_labels() -> None:
    found = []
    for rel, content in iter_pages():
        m = FAKE_LABEL_RE.findall(content)
        if m:
            found.append(f"{rel}: {m}")
    if found:
        for item in found:
            fail(f"FAKE-LABEL: {item}")
    else:
        ok("No hardcoded fake-data labels found")


# ─── Gate 6: High-priority stubs in backend (bare-pass endpoints) ────────────

HIGH_PRIORITY_STUB_FILES = [
    ("nemsis_manager_router.py", "validate/cross-field-consistency"),
    ("scheduling_router.py", "fatigue/report"),
    ("tracking_router.py", "track/{token}"),
]


def gate_no_critical_stubs() -> None:
    for fname, label in HIGH_PRIORITY_STUB_FILES:
        fpath = os.path.join(BACKEND_API, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, errors="replace") as f:
            content = f.read()
        if BARE_PASS_RE.search(content):
            fail(f"STUB-ENDPOINT: {fname} contains bare-pass ({label})")
        else:
            ok(f"No bare-pass in {fname}")


# ─── Gate 7: Fax inbox endpoint exists ───────────────────────────────────────

FAX_ROUTER = os.path.join(BACKEND_API, "fax_router.py")


def gate_fax_inbox_exists() -> None:
    if not os.path.exists(FAX_ROUTER):
        fail("FAX-ROUTER-MISSING")
        return
    with open(FAX_ROUTER, errors="replace") as f:
        content = f.read()
    if '"/fax/inbox"' not in content and "'/fax/inbox'" not in content:
        fail("MISSING-ENDPOINT: GET /api/v1/fax/inbox not in fax_router.py (portal/fax-inbox is broken)")
    else:
        ok("Fax inbox endpoint exists")


# ─── Gate 8: auth-rep OTP endpoints present ──────────────────────────────────

AUTH_REP_ROUTER = os.path.join(BACKEND_API, "auth_rep_router.py")


def gate_auth_rep_paths() -> None:
    if not os.path.exists(AUTH_REP_ROUTER):
        fail("AUTH-REP-ROUTER-MISSING")
        return
    with open(AUTH_REP_ROUTER, errors="replace") as f:
        content = f.read()
    for path in ["/otp/request", "/otp/verify", "/sign"]:
        if f'"{path}"' not in content and f"'{path}'" not in content:
            fail(f"MISSING-ENDPOINT: /api/v1/auth-rep{path} — portal/rep pages will 404")
        else:
            ok(f"auth-rep{path} exists")


# ─── Gate 9: HEMS page has SSE or polling (realtime mandate) ─────────────────

SSE_RE = re.compile(r"EventSource|useWebSocket|setInterval.*fetch")


def gate_hems_has_realtime() -> None:
    if not os.path.exists(HEMS_PAGE):
        fail("HEMS-PAGE-MISSING")
        return
    with open(HEMS_PAGE, errors="replace") as f:
        content = f.read()
    if not SSE_RE.search(content):
        fail(
            "HEMS-NO-REALTIME: portal/hems/page.tsx has no EventSource/WebSocket/polling — "
            "violates HEMS realtime mandate"
        )
    else:
        ok("HEMS page has realtime (SSE or polling)")


# ─── Gate 10: Founder compliance status endpoint exists ──────────────────────

def gate_founder_compliance_status() -> None:
    paths = collect_backend_paths()
    target = norm("/api/v1/founder/compliance/status")
    if target not in {norm(p) for p in paths}:
        fail("MISSING-ENDPOINT: GET /api/v1/founder/compliance/status (founder dashboard broken)")
    else:
        ok("founder/compliance/status endpoint exists")


# ─── Run all gates ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CI Gate: Route Matrix + Endpoint Coverage + HEMS")
    print("=" * 60)

    gate_known_mismatches()
    gate_required_endpoints()
    gate_hems_no_silent_catches()
    gate_hems_not_stub()
    gate_no_fake_labels()
    gate_no_critical_stubs()
    gate_fax_inbox_exists()
    gate_auth_rep_paths()
    gate_hems_has_realtime()
    gate_founder_compliance_status()

    print()
    print("=" * 60)
    if failures:
        print(f"FAILED: {len(failures)} gate(s) failed")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL GATES PASSED")
        sys.exit(0)
