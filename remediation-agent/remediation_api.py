"""
Remediation API — deploy this on the Azure VM (inside VNet).
Run with: uvicorn remediation_api:app --host 0.0.0.0 --port 8000
"""

import os
import subprocess
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Remediation API", version="1.0")

CONTAINER_NAME  = os.getenv("CONTAINER_NAME",  "pepsi-fastapi-aci")
RESOURCE_GROUP  = os.getenv("RESOURCE_GROUP",  "pep-network-poc-01")
SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID", "501702e0-f393-47f4-9aa9-3a47cde4c238")

# ── Action registry ───────────────────────────────────────────────────────────
def _az(*args):
    return ["az", "--subscription", SUBSCRIPTION_ID] + list(args)

ACTION_MAP = {
    "restart_container": _az(
        "container", "restart",
        "--name",           CONTAINER_NAME,
        "--resource-group", RESOURCE_GROUP
    ),
    "check_routing": _az(
        "network", "application-gateway", "show",
        "--name",           "poc-gateway",
        "--resource-group", RESOURCE_GROUP,
        "--output",         "table"
    ),
    "check_sql_identity": _az(
        "container", "show",
        "--name",           CONTAINER_NAME,
        "--resource-group", RESOURCE_GROUP,
        "--query",          "identity",
        "--output",         "json"
    ),
    "show_container_logs": _az(
        "container", "logs",
        "--name",           CONTAINER_NAME,
        "--resource-group", RESOURCE_GROUP,
        "--tail",           "50"
    ),
    "show_container_status": _az(
        "container", "show",
        "--name",           CONTAINER_NAME,
        "--resource-group", RESOURCE_GROUP,
        "--query",          "instanceView.state",
        "--output",         "tsv"
    ),
}

# ── Models ────────────────────────────────────────────────────────────────────
class RemediationRequest(BaseModel):
    action: str
    reason: str  = ""
    issue_code: str = ""

class RemediationResult(BaseModel):
    action: str
    success: bool
    stdout: str
    stderr: str
    returncode: int
    executed_at: str

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/actions")
def list_actions():
    return {"available_actions": list(ACTION_MAP.keys())}

@app.post("/remediate", response_model=RemediationResult)
def remediate(req: RemediationRequest):
    cmd = ACTION_MAP.get(req.action)
    if not cmd:
        raise HTTPException(status_code=400, detail=f"Unknown action '{req.action}'. Available: {list(ACTION_MAP.keys())}")

    log.info(f"Executing action={req.action} | issue={req.issue_code} | reason={req.reason}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Command timed out after 120s")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="az CLI not found on this VM — install Azure CLI first")

    success = result.returncode == 0
    log.info(f"Action={req.action} returncode={result.returncode} success={success}")

    return RemediationResult(
        action=req.action,
        success=success,
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
        returncode=result.returncode,
        executed_at=datetime.utcnow().isoformat()
    )
