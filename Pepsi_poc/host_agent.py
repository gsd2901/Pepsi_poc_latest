"""
host_agent.py — Run this directly on windows-poc-vm (outside Docker)
It listens on port 9000 and executes Docker commands on behalf of the FastAPI container.

Usage:
    pip install flask
    python host_agent.py

Keep this running in the background using:
    pythonw host_agent.py   (Windows, no console window)
"""

from flask import Flask, jsonify, request
import subprocess
import logging
from datetime import datetime, timezone

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONTAINER_NAME = "pepsi-fastapi"
IMAGE_NAME = "pepsicoappregistry.azurecr.io/myapp:latest"
ACR_NAME = "pepsicoappregistry"

DOCKER_RUN_CMD = (
    f'docker run -d '
    f'--name {CONTAINER_NAME} '
    f'-p 8000:8000 '
    f'-e "ENVIRONMENT=production" '
    f'-e "SECRET_KEY=PepsiPoc@AzureSecretKey2026!" '
    f'-e "DATABASE_URL=mssql+pyodbc://placeholder" '
    f'-e "APPINSIGHTS_APP_ID=350d7c0a-0383-4814-8dba-8773452dee12" '
    f'-e "APPINSIGHTS_API_KEY=ib74dfcgxcqqil67cgsuo6abadcvfdcfwk6q0nnm" '
    f'-e "HOST_AGENT_URL=http://host.docker.internal:9000" '
    f'-e "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=d5ff943e-9f73-413e-883e-0071b107eabf;'
    f'IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/;'
    f'LiveEndpoint=https://eastus.livediagnostics.monitor.azure.com/;'
    f'ApplicationId=350d7c0a-0383-4814-8dba-8773452dee12" '
    f'{IMAGE_NAME}'
)


def run_cmd(cmd: str) -> tuple[str, str, int]:
    """Run a shell command and return stdout, stderr, returncode."""
    logger.info(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


@app.route("/status", methods=["GET"])
def status():
    """Return current container status."""
    stdout, stderr, code = run_cmd(f"docker inspect --format={{{{.State.Status}}}} {CONTAINER_NAME}")
    if code != 0:
        return jsonify({
            "container": CONTAINER_NAME,
            "status": "not_found",
            "healthy": False,
            "checked_at": datetime.now(timezone.utc).isoformat()
        })

    # Get uptime
    uptime_out, _, _ = run_cmd(
        f'docker inspect --format={{{{.State.StartedAt}}}} {CONTAINER_NAME}'
    )

    return jsonify({
        "container": CONTAINER_NAME,
        "status": stdout,
        "healthy": stdout == "running",
        "started_at": uptime_out,
        "checked_at": datetime.now(timezone.utc).isoformat()
    })


@app.route("/restart", methods=["POST"])
def restart():
    """Restart the container (stop → rm → run)."""
    body = request.json or {}
    reason = body.get("reason", "Manual restart")
    logger.info(f"Restart requested: {reason}")

    steps = []

    # Stop
    out, err, code = run_cmd(f"docker stop {CONTAINER_NAME}")
    steps.append({"step": "stop", "success": code == 0, "output": out or err})

    # Remove
    out, err, code = run_cmd(f"docker rm {CONTAINER_NAME}")
    steps.append({"step": "remove", "success": code == 0, "output": out or err})

    # Start
    out, err, code = run_cmd(DOCKER_RUN_CMD)
    steps.append({"step": "start", "success": code == 0, "output": out or err})

    overall_success = all(s["success"] for s in steps[-1:])  # only care if start succeeded

    return jsonify({
        "action": "restart",
        "reason": reason,
        "success": overall_success,
        "steps": steps,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }), 200 if overall_success else 500


@app.route("/redeploy", methods=["POST"])
def redeploy():
    """Pull latest image from ACR and redeploy container."""
    body = request.json or {}
    reason = body.get("reason", "Manual redeploy")
    logger.info(f"Redeploy requested: {reason}")

    steps = []

    # ACR login
    out, err, code = run_cmd(f"az acr login --name {ACR_NAME}")
    steps.append({"step": "acr_login", "success": code == 0, "output": out or err})

    # Pull latest image
    out, err, code = run_cmd(f"docker pull {IMAGE_NAME}")
    steps.append({"step": "pull_image", "success": code == 0, "output": out or err})

    if code != 0:
        return jsonify({
            "action": "redeploy",
            "reason": reason,
            "success": False,
            "steps": steps,
            "error": "Image pull failed — aborting redeploy",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }), 500

    # Stop + remove existing
    out, err, code = run_cmd(f"docker stop {CONTAINER_NAME}")
    steps.append({"step": "stop", "success": code == 0, "output": out or err})

    out, err, code = run_cmd(f"docker rm {CONTAINER_NAME}")
    steps.append({"step": "remove", "success": code == 0, "output": out or err})

    # Start with new image
    out, err, code = run_cmd(DOCKER_RUN_CMD)
    steps.append({"step": "start", "success": code == 0, "output": out or err})

    overall_success = code == 0

    return jsonify({
        "action": "redeploy",
        "reason": reason,
        "success": overall_success,
        "steps": steps,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }), 200 if overall_success else 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent": "host-agent", "port": 9000})


if __name__ == "__main__":
    logger.info("Starting Host Agent on port 9000...")
    app.run(host="0.0.0.0", port=9000, debug=False)
