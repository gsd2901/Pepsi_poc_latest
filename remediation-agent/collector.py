import requests
import os
from datetime import datetime

APP_ID  = os.getenv("APPINSIGHTS_APP_ID")
API_KEY = os.getenv("APPINSIGHTS_API_KEY")

BASE_URL = f"https://api.applicationinsights.io/v1/apps/{APP_ID}/query"

QUERIES = {
    "requests": """
        requests
        | where timestamp > ago(1h)
        | summarize count() by resultCode, name
        | order by count_ desc
    """,
    "exceptions": """
        exceptions
        | where timestamp > ago(1h)
        | summarize count() by type, outerMessage
        | order by count_ desc
    """,
    "dependencies": """
        dependencies
        | where timestamp > ago(1h)
        | where success == false
        | summarize count() by type, name, resultCode
        | order by count_ desc
    """,
    "no_telemetry_check": """
        requests
        | where timestamp > ago(10m)
        | count
    """
}

def fetch(query_name: str) -> dict:
    query = QUERIES.get(query_name)
    if not query:
        raise ValueError(f"Unknown query: {query_name}")

    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    resp = requests.post(BASE_URL, headers=headers, json={"query": query}, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    tables = data.get("tables", [])
    if not tables:
        return {"columns": [], "rows": []}

    cols = [c["name"] for c in tables[0]["columns"]]
    rows = tables[0]["rows"]
    return {"columns": cols, "rows": rows, "fetched_at": datetime.utcnow().isoformat()}

def fetch_all() -> dict:
    results = {}
    for name in QUERIES:
        try:
            results[name] = fetch(name)
        except Exception as e:
            results[name] = {"error": str(e), "columns": [], "rows": []}
    return results
