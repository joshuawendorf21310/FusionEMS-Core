import os, requests, sys
base = os.environ.get("BASE_URL")
if not base:
    print("BASE_URL required")
    sys.exit(2)
r = requests.get(base.rstrip("/") + "/api/v1/health", timeout=10)
print(r.status_code, r.text)
assert r.status_code == 200
