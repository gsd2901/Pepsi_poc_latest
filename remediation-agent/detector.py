"""
Detection Engine
Analyzes telemetry and returns structured issue objects.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Issue:
    code: str
    confidence: float
    reason: str
    action: str
    severity: str   # low / medium / high / critical

    def dict(self):
        return self.__dict__


def detect(telemetry: dict) -> Optional[Issue]:
    """
    Run all detectors in priority order.
    Returns the highest-priority issue found, or None.
    """
    detectors = [
        _detect_no_telemetry,
        _detect_5xx_spike,
        _detect_404_flood,
        _detect_sql_failures,
        _detect_dependency_failures,
    ]
    for fn in detectors:
        issue = fn(telemetry)
        if issue:
            return issue
    return None


# ── Individual detectors ──────────────────────────────────────────────────────

def _detect_no_telemetry(t: dict) -> Optional[Issue]:
    check = t.get("no_telemetry_check", {})
    rows  = check.get("rows", [])
    if not rows:
        return None
    count = rows[0][0] if rows[0] else 0
    if count == 0:
        return Issue(
            code="err_no_telemetry",
            confidence=0.97,
            reason="Zero requests in last 10 minutes — app may be down or App Insights disconnected",
            action="restart_container",
            severity="critical"
        )
    return None


def _detect_5xx_spike(t: dict) -> Optional[Issue]:
    rows = t.get("requests", {}).get("rows", [])
    total_5xx = 0
    worst_endpoint = ""
    for row in rows:
        code, name, count = str(row[0]), str(row[1]), int(row[2])
        if code.startswith("5"):
            total_5xx += count
            if not worst_endpoint:
                worst_endpoint = name
    if total_5xx > 10:
        confidence = min(0.99, 0.80 + (total_5xx / 200))
        return Issue(
            code="err_5xx_spike",
            confidence=round(confidence, 2),
            reason=f"{total_5xx} server errors in last 1h — worst on '{worst_endpoint}'",
            action="restart_container",
            severity="critical" if total_5xx > 50 else "high"
        )
    return None


def _detect_404_flood(t: dict) -> Optional[Issue]:
    rows = t.get("requests", {}).get("rows", [])
    total_404 = 0
    endpoints = []
    for row in rows:
        code, name, count = str(row[0]), str(row[1]), int(row[2])
        if code == "404":
            total_404 += count
            endpoints.append(name)
    if total_404 > 20:
        return Issue(
            code="err_404_flood",
            confidence=0.88,
            reason=f"{total_404} 404 errors — missing endpoints: {', '.join(endpoints[:3])}",
            action="check_routing",
            severity="medium"
        )
    return None


def _detect_sql_failures(t: dict) -> Optional[Issue]:
    rows = t.get("dependencies", {}).get("rows", [])
    sql_failures = 0
    for row in rows:
        dep_type, name, result_code, count = str(row[0]), str(row[1]), str(row[2]), int(row[3])
        if "SQL" in dep_type or "sql" in name.lower():
            sql_failures += count
    if sql_failures > 5:
        return Issue(
            code="err_sql_failure",
            confidence=0.91,
            reason=f"{sql_failures} SQL dependency failures — possible identity or connection issue",
            action="check_sql_identity",
            severity="high"
        )
    return None


def _detect_dependency_failures(t: dict) -> Optional[Issue]:
    rows = t.get("dependencies", {}).get("rows", [])
    total = sum(int(r[3]) for r in rows) if rows else 0
    if total > 15:
        return Issue(
            code="err_dependency",
            confidence=0.82,
            reason=f"{total} external dependency failures in last 1h",
            action="check_routing",
            severity="medium"
        )
    return None
