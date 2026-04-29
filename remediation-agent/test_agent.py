"""
Run this first to verify everything works before starting the agent.
  python test_agent.py
"""

import os
from dotenv import load_dotenv
load_dotenv()

print("=" * 55)
print("  Agent smoke test")
print("=" * 55)

# 1. Test App Insights connectivity
print("\n[1] Testing App Insights connectivity...")
try:
    from collector import fetch_all
    telemetry = fetch_all()
    for name, data in telemetry.items():
        if "error" in data:
            print(f"  ✗ {name}: {data['error']}")
        else:
            print(f"  ✓ {name}: {len(data['rows'])} rows returned")
except Exception as e:
    print(f"  ✗ FAILED: {e}")

# 2. Test detection engine
print("\n[2] Running detection engine on fetched telemetry...")
try:
    from detector import detect
    issue = detect(telemetry)
    if issue:
        print(f"  ✓ Issue detected:")
        print(f"      code       : {issue.code}")
        print(f"      severity   : {issue.severity}")
        print(f"      confidence : {issue.confidence}")
        print(f"      action     : {issue.action}")
        print(f"      reason     : {issue.reason}")
    else:
        print("  ✓ No issues detected — system appears healthy")
except Exception as e:
    print(f"  ✗ FAILED: {e}")

# 3. Test Remediation API health
print("\n[3] Testing Remediation API health...")
import requests as req
api_url = os.getenv("REMEDIATION_API_URL", "http://localhost:8000")
try:
    resp = req.get(f"{api_url}/health", timeout=5)
    print(f"  ✓ API reachable: {resp.json()}")
except Exception as e:
    print(f"  ✗ API not reachable at {api_url}: {e}")
    print(f"     → Start it on Azure VM with: uvicorn remediation_api:app --host 0.0.0.0 --port 8000")

print("\n" + "=" * 55)
print("  Done. Fix any ✗ above before running agent.py")
print("=" * 55)
