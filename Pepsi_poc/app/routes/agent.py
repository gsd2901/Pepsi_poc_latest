import os
import httpx
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

router = APIRouter()

APP_INSIGHTS_APP_ID = os.getenv("APPINSIGHTS_APP_ID", "350d7c0a-0383-4814-8dba-8773452dee12")
APP_INSIGHTS_API_KEY = os.getenv("APPINSIGHTS_API_KEY", "")
HOST_AGENT_URL = os.getenv("HOST_AGENT_URL", "http://host.docker.internal:9000")

HEADERS = {"x-api-key": APP_INSIGHTS_API_KEY}
BASE_URL = f"https://api.applicationinsights.io/v1/apps/{APP_INSIGHTS_APP_ID}/query"


async def run_kql(query: str) -> dict:
    """Execute a KQL query against App Insights REST API."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(BASE_URL, params={"query": query}, headers=HEADERS)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"App Insights query failed: {response.text}")
        data = response.json()
        table = data["tables"][0]
        columns = [col["name"] for col in table["columns"]]
        rows = [dict(zip(columns, row)) for row in table["rows"]]
        return {"count": len(rows), "data": rows}


# ─────────────────────────────────────────────
# DIAGNOSTICS ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/logs/requests")
async def get_recent_requests(minutes: int = 30, limit: int = 20):
    """Fetch recent HTTP requests from App Insights."""
    query = f"""
    requests
    | where timestamp > ago({minutes}m)
    | project timestamp, name, url, success, resultCode, duration, operation_Id
    | order by timestamp desc
    | take {limit}
    """
    result = await run_kql(query)
    return {
        "tool": "fetch_recent_requests",
        "window_minutes": minutes,
        **result
    }


@router.get("/logs/errors")
async def get_errors(minutes: int = 30, limit: int = 20):
    """Fetch failed requests (4xx and 5xx) from App Insights."""
    query = f"""
    requests
    | where timestamp > ago({minutes}m)
    | where success == false or toint(resultCode) >= 400
    | project timestamp, name, url, resultCode, duration, operation_Id
    | order by timestamp desc
    | take {limit}
    """
    result = await run_kql(query)
    return {
        "tool": "fetch_errors",
        "window_minutes": minutes,
        **result
    }


@router.get("/logs/exceptions")
async def get_exceptions(minutes: int = 60, limit: int = 20):
    """Fetch exceptions with stack traces from App Insights."""
    query = f"""
    exceptions
    | where timestamp > ago({minutes}m)
    | project timestamp, type, message, outerMessage, innermostMessage, operation_Name, operation_Id
    | order by timestamp desc
    | take {limit}
    """
    result = await run_kql(query)
    return {
        "tool": "fetch_exceptions",
        "window_minutes": minutes,
        **result
    }


@router.get("/logs/slow")
async def get_slow_requests(minutes: int = 30, threshold_ms: int = 500, limit: int = 20):
    """Fetch requests exceeding the duration threshold."""
    query = f"""
    requests
    | where timestamp > ago({minutes}m)
    | where duration > {threshold_ms}
    | project timestamp, name, url, duration, resultCode, operation_Id
    | order by duration desc
    | take {limit}
    """
    result = await run_kql(query)
    return {
        "tool": "fetch_slow_requests",
        "threshold_ms": threshold_ms,
        "window_minutes": minutes,
        **result
    }


@router.get("/logs/summary")
async def get_health_summary(minutes: int = 30):
    """Overall health summary — request counts, error rate, avg duration."""
    query = f"""
    requests
    | where timestamp > ago({minutes}m)
    | summarize
        total_requests = count(),
        failed_requests = countif(success == false),
        avg_duration_ms = round(avg(duration), 2),
        max_duration_ms = round(max(duration), 2),
        success_rate = round(100.0 * countif(success == true) / count(), 2)
    """
    result = await run_kql(query)

    exceptions_query = f"""
    exceptions
    | where timestamp > ago({minutes}m)
    | summarize exception_count = count()
    """
    exc_result = await run_kql(exceptions_query)

    summary = result["data"][0] if result["data"] else {}
    exc_summary = exc_result["data"][0] if exc_result["data"] else {}

    # Determine overall health
    success_rate = summary.get("success_rate", 100)
    exception_count = exc_summary.get("exception_count", 0)

    if success_rate >= 99 and exception_count == 0:
        health_status = "HEALTHY"
    elif success_rate >= 95 or exception_count < 5:
        health_status = "DEGRADED"
    else:
        health_status = "UNHEALTHY"

    return {
        "tool": "fetch_health_summary",
        "window_minutes": minutes,
        "health_status": health_status,
        "metrics": {**summary, **exc_summary},
        "checked_at": datetime.now(timezone.utc).isoformat()
    }


# ─────────────────────────────────────────────
# REMEDIATION ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/remediate/status")
async def get_container_status():
    """Check current container status via host agent."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{HOST_AGENT_URL}/status")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Host agent unreachable: {str(e)}")


@router.post("/remediate/restart")
async def restart_container(reason: str = "Agent triggered restart"):
    """Restart the FastAPI container via host agent."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{HOST_AGENT_URL}/restart",
                json={"reason": reason, "triggered_at": datetime.now(timezone.utc).isoformat()}
            )
            return {
                "tool": "remediate_restart",
                "action": "container_restart",
                "reason": reason,
                "result": response.json()
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Restart failed: {str(e)}")


@router.post("/remediate/redeploy")
async def redeploy_container(reason: str = "Agent triggered redeploy"):
    """Pull latest image from ACR and redeploy container via host agent."""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{HOST_AGENT_URL}/redeploy",
                json={"reason": reason, "triggered_at": datetime.now(timezone.utc).isoformat()}
            )
            return {
                "tool": "remediate_redeploy",
                "action": "container_redeploy",
                "reason": reason,
                "result": response.json()
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redeploy failed: {str(e)}")