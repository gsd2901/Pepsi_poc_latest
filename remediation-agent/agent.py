"""
Autonomous Remediation Agent
Run on Lab VM: python agent.py
"""

import os
import time
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from collector import fetch_all
from detector  import detect, Issue

# ── Config ────────────────────────────────────────────────────────────────────
REMEDIATION_API   = os.getenv("REMEDIATION_API_URL",      "http://localhost:8000")
POLL_INTERVAL     = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
CONF_THRESHOLD    = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))
VALIDATE_DELAY    = 60   # seconds to wait before validating fix

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent.log")
    ]
)
log = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────
def call_remediation_api(issue: Issue) -> dict:
    url = f"{REMEDIATION_API}/remediate"
    payload = {
        "action":     issue.action,
        "reason":     issue.reason,
        "issue_code": issue.code
    }
    try:
        resp = requests.post(url, json=payload, timeout=130)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        log.error(f"Cannot reach Remediation API at {REMEDIATION_API}. Is it running on the Azure VM?")
        return {"success": False, "error": "connection_refused"}
    except Exception as e:
        log.error(f"Remediation API error: {e}")
        return {"success": False, "error": str(e)}

def validate_recovery(original_issue: Issue) -> bool:
    log.info(f"Waiting {VALIDATE_DELAY}s before validation...")
    time.sleep(VALIDATE_DELAY)
    log.info("Fetching telemetry to validate recovery...")
    telemetry = fetch_all()
    new_issue  = detect(telemetry)
    if new_issue and new_issue.code == original_issue.code:
        log.warning(f"[VALIDATION FAILED] Issue '{original_issue.code}' still present after remediation")
        return False
    log.info(f"[VALIDATION OK] Issue '{original_issue.code}' resolved")
    return True

def check_api_health() -> bool:
    try:
        resp = requests.get(f"{REMEDIATION_API}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

# ── Main loop ─────────────────────────────────────────────────────────────────
def run():
    log.info("=" * 60)
    log.info("  Autonomous Remediation Agent starting up")
    log.info(f"  Remediation API : {REMEDIATION_API}")
    log.info(f"  Poll interval   : {POLL_INTERVAL}s")
    log.info(f"  Confidence threshold: {CONF_THRESHOLD}")
    log.info("=" * 60)

    if not check_api_health():
        log.warning(f"Remediation API not reachable at {REMEDIATION_API} — will retry each cycle")

    while True:
        cycle_start = datetime.utcnow().isoformat()
        log.info(f"--- Polling cycle at {cycle_start} ---")

        try:
            # 1. Collect
            log.info("Fetching telemetry from App Insights...")
            telemetry = fetch_all()

            # 2. Detect
            issue = detect(telemetry)

            if not issue:
                log.info("No issues detected. System healthy.")

            elif issue.confidence < CONF_THRESHOLD:
                log.info(
                    f"Issue detected but confidence too low "
                    f"({issue.confidence} < {CONF_THRESHOLD}): {issue.reason}"
                )

            else:
                # 3. Remediate
                log.warning(
                    f"[ISSUE] code={issue.code} severity={issue.severity} "
                    f"confidence={issue.confidence}\n  → {issue.reason}"
                )
                log.info(f"Triggering action: {issue.action}")

                result = call_remediation_api(issue)

                if result.get("success"):
                    log.info(f"[REMEDIATED] Action '{issue.action}' executed successfully")
                    log.info(f"  stdout: {result.get('stdout', '')[:200]}")

                    # 4. Validate
                    recovered = validate_recovery(issue)
                    if not recovered:
                        log.error(
                            f"[ESCALATE] Issue '{issue.code}' persists after remediation. "
                            f"Manual intervention required."
                        )
                else:
                    log.error(
                        f"[REMEDIATION FAILED] action={issue.action} "
                        f"error={result.get('error') or result.get('stderr')}"
                    )

        except Exception as e:
            log.exception(f"Unexpected error in agent loop: {e}")

        log.info(f"Sleeping {POLL_INTERVAL}s until next cycle...\n")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
