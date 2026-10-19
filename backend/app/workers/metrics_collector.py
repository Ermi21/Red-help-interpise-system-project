"""
Background metrics collector — runs every 15 seconds.

Collects CPU / RAM / disk / network stats via psutil, writes a row to
system_metrics, and publishes alert events when thresholds are breached.

The worker is started as an asyncio background task from app.main lifespan.
"""
import asyncio
from datetime import datetime, timezone

from app.core.event_bus import publish_event
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Thresholds that trigger warning / critical events
_THRESHOLDS = {
    "cpu_warning":   80.0,
    "cpu_critical":  95.0,
    "mem_warning":   80.0,
    "mem_critical":  95.0,
    "disk_warning":  80.0,
    "disk_critical": 95.0,
}

# Track whether we are already in an alerted state so we don't spam events
_alert_state: dict[str, bool] = {}

# Simple in-process request counter updated by the logging middleware
_request_counters: dict[str, float] = {
    "total": 0,
    "errors": 0,
    "latency_sum": 0.0,
    "latency_count": 0,
}


def record_request(status_code: int, latency_ms: float) -> None:
    """Called by RequestLoggingMiddleware for every completed request."""
    _request_counters["total"] += 1
    if status_code >= 400:
        _request_counters["errors"] += 1
    _request_counters["latency_sum"] += latency_ms
    _request_counters["latency_count"] += 1


def _drain_request_counters() -> dict:
    """Return current counters and reset them for the next interval."""
    total = int(_request_counters["total"])
    errors = int(_request_counters["errors"])
    lcount = _request_counters["latency_count"]
    avg_ms = (_request_counters["latency_sum"] / lcount) if lcount else 0.0
    _request_counters["total"] = 0
    _request_counters["errors"] = 0
    _request_counters["latency_sum"] = 0.0
    _request_counters["latency_count"] = 0
    return {"requests_total": total, "requests_error": errors, "avg_latency_ms": round(avg_ms, 2)}


async def _collect_once() -> None:
    """Collect one sample, write to DB, fire events if needed."""
    try:
        import psutil

        now = datetime.now(timezone.utc)
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        req = _drain_request_counters()

        # Persist metric row in background thread
        def _save_metric():
            from app.database.connection import app_session
            from app.models.system_metrics import SystemMetric
            with app_session() as session:
                session.add(SystemMetric(
                    collected_at=now,
                    cpu_percent=round(cpu, 1),
                    cpu_count=psutil.cpu_count(logical=True),
                    mem_total_mb=round(mem.total / 1_048_576, 0),
                    mem_used_mb=round(mem.used / 1_048_576, 0),
                    mem_percent=round(mem.percent, 1),
                    disk_total_gb=round(disk.total / 1_073_741_824, 1),
                    disk_used_gb=round(disk.used / 1_073_741_824, 1),
                    disk_percent=round(disk.percent, 1),
                    net_bytes_sent=net.bytes_sent,
                    net_bytes_recv=net.bytes_recv,
                    requests_total=req["requests_total"],
                    requests_error=req["requests_error"],
                    avg_latency_ms=req["avg_latency_ms"],
                ))
        await asyncio.to_thread(_save_metric)

        # Fire threshold events (but not on every sample to avoid spam)
        await _check_threshold("cpu",  cpu,      "CPU usage",  "%")
        await _check_threshold("mem",  mem.percent, "RAM usage", "%")
        await _check_threshold("disk", disk.percent, "Disk usage", "%")

    except ImportError:
        pass  # psutil not installed — skip silently
    except Exception as exc:
        logger.warning("Metrics collector error: %s", exc)


async def _check_threshold(key: str, value: float, label: str, unit: str) -> None:
    warn_key  = f"{key}_warned"
    crit_key  = f"{key}_critical"
    crit_thr  = _THRESHOLDS[f"{key}_critical"]
    warn_thr  = _THRESHOLDS[f"{key}_warning"]

    if value >= crit_thr and not _alert_state.get(crit_key):
        _alert_state[crit_key] = True
        _alert_state[warn_key] = True
        await publish_event(
            source="server",
            event_type=f"{key}_critical",
            severity="critical",
            title=f"{label} critical: {value:.0f}{unit}",
            message=f"{label} has been at {value:.1f}{unit}, above the critical threshold of {crit_thr}{unit}.",
            metadata={f"{key}_percent": value, "threshold": crit_thr},
        )
    elif value >= warn_thr and not _alert_state.get(warn_key):
        _alert_state[warn_key] = True
        await publish_event(
            source="server",
            event_type=f"{key}_warning",
            severity="warning",
            title=f"{label} high: {value:.0f}{unit}",
            message=f"{label} is at {value:.1f}{unit}, above the warning threshold of {warn_thr}{unit}.",
            metadata={f"{key}_percent": value, "threshold": warn_thr},
        )
    elif value < warn_thr:
        # Recovered — reset alert state so it can fire again if it climbs back
        if _alert_state.get(warn_key) or _alert_state.get(crit_key):
            _alert_state[warn_key] = False
            _alert_state[crit_key] = False
            await publish_event(
                source="server",
                event_type=f"{key}_recovered",
                severity="info",
                title=f"{label} recovered: {value:.0f}{unit}",
                message=f"{label} is back to normal at {value:.1f}{unit}.",
                metadata={f"{key}_percent": value},
            )


async def run_metrics_collector(interval_s: int = 15) -> None:
    """
    Main loop — run as `asyncio.create_task(run_metrics_collector())` from
    the FastAPI lifespan.
    """
    logger.info("Metrics collector started (interval=%ds)", interval_s)
    await asyncio.sleep(2)  # Yield to event loop to allow Uvicorn port binding first
    while True:
        await _collect_once()
        await asyncio.sleep(interval_s)
