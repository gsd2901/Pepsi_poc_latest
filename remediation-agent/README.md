# Autonomous Remediation Agent

## Files
| File | Where to run | Purpose |
|------|-------------|---------|
| `.env` | Lab VM | All config |
| `collector.py` | Lab VM | Fetches App Insights telemetry |
| `detector.py` | Lab VM | Classifies issues |
| `agent.py` | Lab VM | Main loop (orchestrator) |
| `remediation_api.py` | Azure VM | Executes az CLI commands |
| `test_agent.py` | Lab VM | Smoke test before going live |

---

## Step 1 — On Azure VM: start Remediation API

```bash
# Copy remediation_api.py and requirements.txt to the Azure VM, then:
pip install fastapi uvicorn pydantic --break-system-packages

export CONTAINER_NAME=pepsi-fastapi-aci
export RESOURCE_GROUP=pep-network-poc-01
export SUBSCRIPTION_ID=501702e0-f393-47f4-9aa9-3a47cde4c238

uvicorn remediation_api:app --host 0.0.0.0 --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/actions
```

---

## Step 2 — On Lab VM: install dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

---

## Step 3 — Update .env with Azure VM IP

Edit `.env` and set:
```
REMEDIATION_API_URL=http://<azure-vm-private-ip>:8000
```

---

## Step 4 — Run smoke test

```bash
python test_agent.py
```

All three checks should show ✓ before proceeding.

---

## Step 5 — Start the agent

```bash
python agent.py
```

Logs go to stdout and `agent.log`.

---

## Detection rules

| Issue | Trigger | Action |
|-------|---------|--------|
| No telemetry | 0 requests in 10 min | restart_container |
| 5xx spike | >10 server errors / 1h | restart_container |
| 404 flood | >20 not-found / 1h | check_routing |
| SQL failures | >5 SQL dep failures / 1h | check_sql_identity |
| Dep failures | >15 any dep failures / 1h | check_routing |
