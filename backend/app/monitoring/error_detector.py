"""
Error detection.

Two sources are covered:
  1. In-process runtime events — connection failures, query failures,
     timeouts, and auth failures are pushed here directly by the code paths
     that encounter them (see app.middleware.error_handler and
     app.database.query_executor), so detection is immediate rather than
     depending on log parsing.
  2. The backend's own rotating JSON log file, scanned for ERROR/CRITICAL
     lines — a fallback net for anything not explicitly instrumented.

This module does not read the target database's server logs directly:
most managed database services don't expose log files to a plain SQL
read-only user, so that integration point is intentionally left as a
pluggable hook (`register_external_log_source`) for a deployment to wire
up against whatever log shipping it already has (CloudWatch, pgAudit
output, etc.) without this backend needing file-system access it may not
have in production.
"""
import json
import os
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Callable

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()
_recent_events: deque[dict] = deque(maxlen=500)

ErrorCategory = str  # "connection" | "query" | "timeout" | "auth" | "api"

_external_log_sources: list[Callable[[], list[dict]]] = []


def record_error_event(category: ErrorCategory, message: str, severity: str = "medium", context: dict | None = None) -> dict:
    event = {
        "category": category,
        "message": message,
        "severity": severity,
        "context": context or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _recent_events.append(event)
    logger.info("Recorded error event", extra={"error_event": event})
    return event


def get_recent_events(limit: int = 100) -> list[dict]:
    with _lock:
        return list(_recent_events)[-limit:]


def register_external_log_source(fetcher: Callable[[], list[dict]]) -> None:
    """Register a callable that returns a list of {category, message,
    severity, timestamp} dicts pulled from an external log source (e.g. a
    cloud log query). Used by scan_backend_logs's aggregate report."""
    _external_log_sources.append(fetcher)


def scan_backend_log_file(max_lines: int = 5000) -> list[dict]:
    """Fallback scan of this backend's own rotating log file for
    ERROR/CRITICAL entries not already captured via record_error_event."""
    settings = get_settings()
    path = os.path.join(settings.log_dir, "backend.log")
    if not os.path.exists(path):
        return []

    found: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-max_lines:]
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("level") in ("ERROR", "CRITICAL"):
                found.append(
                    {
                        "category": "backend_log",
                        "message": record.get("message", ""),
                        "severity": "high" if record.get("level") == "CRITICAL" else "medium",
                        "timestamp": record.get("timestamp"),
                    }
                )
    except OSError as exc:
        logger.warning("Could not read backend log file: %s", exc)

    return found


def build_error_report(limit: int = 100) -> dict:
    events = get_recent_events(limit)
    events += scan_backend_log_file()
    for source in _external_log_sources:
        try:
            events += source()
        except Exception as exc:  # noqa: BLE001
            logger.warning("External log source failed: %s", exc)

    severity_counts: dict[str, int] = {}
    for e in events:
        severity_counts[e["severity"]] = severity_counts.get(e["severity"], 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_events": len(events),
        "by_severity": severity_counts,
        "events": events[-limit:],
    }
