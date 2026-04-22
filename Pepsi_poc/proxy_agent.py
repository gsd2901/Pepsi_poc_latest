"""
host_agent.py — ACI Proxy Agent

Runs on Azure VM (192.168.1.4)
Acts as a bridge between AEX and ACI (10.0.9.5)

Start:
python host_agent.py
"""

from flask import Flask, jsonify, request
import requests
import logging
from datetime import datetime, timezone

# Flask app
app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ACI Base URL
ACI_BASE = "http://10.0.9.5:8000"

# Timeout for all requests
TIMEOUT = 10

# -------------------------
# Helper Function
# -------------------------
def call_aci(method, path, json_body=None):
    url = f"{ACI_BASE}{path}"
    try:
        logger.info(f"Calling ACI: {method} {url}")

        if method == "GET":
            resp = requests.get(url, timeout=TIMEOUT)
        elif method == "POST":
            resp = requests.post(url, json=json_body, timeout=TIMEOUT)
        else:
            return {"error": "Unsupported method"}, 400

        return resp.json(), resp.status_code

    except requests.exceptions.Timeout:
        logger.error("ACI request timed out")
        return {"error": "ACI request timeout"}, 504

    except Exception as e:
        logger.exception("ACI call failed")
        return {"error": str(e)}, 500

# -------------------------
# Health Check
# -------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "agent": "host-agent",
        "target": ACI_BASE,
        "time": datetime.now(timezone.utc).isoformat()
    })

# -------------------------
# Status (Proxy)
# -------------------------
@app.route("/status", methods=["GET"])
def status():
    data, code = call_aci("GET", "/agent/remediate/status")
    return jsonify(data), code

# -------------------------
# Logs Summary (Proxy)
# -------------------------
@app.route("/logs/summary", methods=["GET"])
def logs_summary():
    data, code = call_aci("GET", "/agent/logs/summary")
    return jsonify(data), code

# -------------------------
# Restart (Proxy)
# -------------------------
@app.route("/restart", methods=["POST"])
def restart():
    body = request.json or {}
    reason = body.get("reason", "Triggered via AEX")

    logger.info(f"Restart requested: {reason}")

    data, code = call_aci("POST", "/agent/remediate/restart", {"reason": reason})

    return jsonify({
        "action": "restart",
        "reason": reason,
        "aci_response": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), code

# -------------------------
# Redeploy (Proxy)
# -------------------------
@app.route("/redeploy", methods=["POST"])
def redeploy():
    body = request.json or {}
    reason = body.get("reason", "Triggered via AEX")

    logger.info(f"Redeploy requested: {reason}")

    data, code = call_aci("POST", "/agent/remediate/redeploy", {"reason": reason})

    return jsonify({
        "action": "redeploy",
        "reason": reason,
        "aci_response": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), code

# -------------------------
# Entry Point
# -------------------------
if __name__ == "__main__":
    logger.info("Starting Host Agent (ACI Proxy) on port 9000...")
    app.run(host="0.0.0.0", port=9000, debug=False)