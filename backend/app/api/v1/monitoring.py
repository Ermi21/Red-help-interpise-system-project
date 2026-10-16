"""
Real-time monitoring endpoints for Server, Security, and Database live metrics.
All data is sourced from real infrastructure — no mock values.
"""
import os
import platform
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.api.deps import CurrentUser, get_current_user
from app.database.connection import get_app_engine, get_target_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# ── Per-endpoint TTL caches ────────────────────────────────────────────────────
# Each endpoint caches its last result so Refresh clicks from the UI don't
# hammer the remote Supabase DB on every press. TTLs are short enough that
# the data stays real-time for all practical purposes.
_DB_CACHE_TTL_S    = 30   # /monitoring/database  — refresh every 30 s
_SRV_CACHE_TTL_S   = 15   # /monitoring/server    — CPU/RAM change quickly
_SEC_CACHE_TTL_S   = 60   # /monitoring/security  — security events
_NOTIF_CACHE_TTL_S = 30   # /monitoring/notifications

_db_cache: dict | None = None;    _db_cache_ts:    float = 0.0
_srv_cache: dict | None = None;   _srv_cache_ts:   float = 0.0
_sec_cache: dict | None = None;   _sec_cache_ts:   float = 0.0
_notif_cache: list | None = None; _notif_cache_ts: float = 0.0


def invalidate_all_monitoring_caches() -> None:
    """Force-expire every monitoring cache (e.g. after a new DB connection is applied)."""
    global _db_cache, _db_cache_ts, _srv_cache, _srv_cache_ts
    global _sec_cache, _sec_cache_ts, _notif_cache, _notif_cache_ts
    _db_cache = _srv_cache = _sec_cache = _notif_cache = None
    _db_cache_ts = _srv_cache_ts = _sec_cache_ts = _notif_cache_ts = 0.0
    logger.info("All monitoring caches invalidated")


def _safe_query(engine, sql: str, params: dict | None = None):
    """Execute a read-only query, return first row as dict or None."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            row = result.mappings().first()
            return dict(row) if row else None
    except Exception as e:
        logger.debug("Monitoring query skipped: %s", e)
        return None


def _safe_query_all(engine, sql: str, params: dict | None = None):
    """Execute a read-only query, return all rows as list of dicts."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return [dict(r) for r in result.mappings().all()]
    except Exception as e:
        logger.debug("Monitoring query_all skipped: %s", e)
        return []


# ─────────────────────────────────────────────────────────────
# DATABASE LIVE METRICS
# ─────────────────────────────────────────────────────────────

@router.get("/database")
def get_database_metrics(_: CurrentUser = Depends(get_current_user)):
    """
    Returns real live metrics from the target (Supabase) database.
    Result is cached for 30 s so rapid Refresh clicks don't each
    open a new connection to the remote Supabase pooler.
    """
    global _db_cache, _db_cache_ts
    if _db_cache is not None and (time.monotonic() - _db_cache_ts) < _DB_CACHE_TTL_S:
        logger.debug("monitoring/database cache hit")
        return _db_cache
    metrics: dict[str, Any] = {
        "connection_status": "unknown",
        "database_version": None,
        "active_connections": None,
        "max_connections": None,
        "connection_utilization_pct": None,
        "database_size_bytes": None,
        "database_size_human": None,
        "schema_count": None,
        "table_count": None,
        "slow_query_count": None,
        "cache_hit_ratio": None,
        "total_transactions": None,
        "deadlocks": None,
        "temp_files": None,
        "uptime_seconds": None,
        "errors": [],
        "permissions_note": None,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    # Single batched SQL — all 8 previously-sequential queries combined into one
    # round-trip using CTEs. Only one connection is opened instead of 9.
    BATCHED_SQL = """
    WITH
      ver_cte AS (SELECT version() AS ver),
      conn_cte AS (
        SELECT count(*) AS active
        FROM pg_stat_activity
        WHERE state = 'active'
      ),
      size_cte AS (
        SELECT pg_database_size(current_database()) AS size_bytes
      ),
      schema_cte AS (
        SELECT count(*) AS schema_count
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast')
      ),
      table_cte AS (
        SELECT count(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog','information_schema','pg_toast')
          AND table_type = 'BASE TABLE'
      ),
      cache_cte AS (
        SELECT
          CASE WHEN (sum(blks_hit) + sum(blks_read)) = 0 THEN NULL
               ELSE round(100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2)
          END AS cache_hit_ratio
        FROM pg_stat_database
      ),
      stat_cte AS (
        SELECT
          sum(xact_commit + xact_rollback) AS total_transactions,
          sum(deadlocks)                   AS deadlocks,
          sum(temp_files)                  AS temp_files
        FROM pg_stat_database
      )
    SELECT
      (SELECT ver          FROM ver_cte)            AS db_version,
      (SELECT active       FROM conn_cte)           AS active_connections,
      (SELECT size_bytes   FROM size_cte)           AS size_bytes,
      (SELECT schema_count FROM schema_cte)         AS schema_count,
      (SELECT table_count  FROM table_cte)          AS table_count,
      (SELECT cache_hit_ratio FROM cache_cte)       AS cache_hit_ratio,
      (SELECT total_transactions FROM stat_cte)     AS total_transactions,
      (SELECT deadlocks    FROM stat_cte)           AS deadlocks,
      (SELECT temp_files   FROM stat_cte)           AS temp_files
    """

    # max_connections requires SHOW which cannot go inside a CTE — one extra
    # call still on the same connection via the _safe_query helper.
    try:
        engine = get_target_engine()

        # Open ONE connection and run all three statements inside it
        with engine.connect() as conn:
            # 1. Main batched CTE
            row = conn.execute(text(BATCHED_SQL)).mappings().first()
            row = dict(row) if row else None

            if row:
                metrics["connection_status"] = "connected"

                ver_str = row.get("db_version") or ""
                metrics["database_version"] = " ".join(ver_str.split()[:3])
                metrics["active_connections"] = row.get("active_connections")

                size_bytes = row.get("size_bytes") or 0
                metrics["database_size_bytes"] = size_bytes
                if size_bytes > 1_073_741_824:
                    metrics["database_size_human"] = f"{size_bytes / 1_073_741_824:.2f} GB"
                elif size_bytes > 1_048_576:
                    metrics["database_size_human"] = f"{size_bytes / 1_048_576:.2f} MB"
                else:
                    metrics["database_size_human"] = f"{size_bytes / 1024:.1f} KB"

                metrics["schema_count"] = row.get("schema_count")
                metrics["table_count"] = row.get("table_count")

                cache_ratio = row.get("cache_hit_ratio")
                if cache_ratio is not None:
                    metrics["cache_hit_ratio"] = float(cache_ratio)

                metrics["total_transactions"] = int(row.get("total_transactions") or 0)
                metrics["deadlocks"]          = int(row.get("deadlocks")          or 0)
                metrics["temp_files"]         = int(row.get("temp_files")         or 0)

                # 2. SHOW max_connections — same open connection, no extra round-trip
                try:
                    mc_row = conn.execute(text("SHOW max_connections")).mappings().first()
                    if mc_row:
                        metrics["max_connections"] = int(list(dict(mc_row).values())[0])
                        if metrics["active_connections"] is not None and metrics["max_connections"]:
                            metrics["connection_utilization_pct"] = round(
                                (metrics["active_connections"] / metrics["max_connections"]) * 100, 1
                            )
                except Exception:
                    pass

                # 3. pg_stat_statements (optional extension)
                try:
                    slow_row = conn.execute(text(
                        "SELECT count(*) AS cnt FROM pg_stat_statements WHERE mean_exec_time > 1000"
                    )).mappings().first()
                    metrics["slow_query_count"] = int(dict(slow_row)["cnt"]) if slow_row else None
                except Exception:
                    metrics["slow_query_count"] = None

            else:
                metrics["connection_status"] = "degraded"

    except Exception as exc:
        metrics["connection_status"] = "error"
        metrics["errors"].append(str(exc))
        logger.warning("Database metrics collection failed: %s", exc)

    # Cache the result (even on partial failure so we don't hammer the DB)
    _db_cache = metrics
    _db_cache_ts = time.monotonic()
    return metrics


# ─────────────────────────────────────────────────────────────
# SERVER / SYSTEM LIVE METRICS (local host running the backend)
# ─────────────────────────────────────────────────────────────

@router.get("/server")
def get_server_metrics(_: CurrentUser = Depends(get_current_user)):
    """
    Returns real live metrics from the server running this backend service.
    Cached for 15 s — CPU/RAM values are accurate to within one polling cycle.
    """
    global _srv_cache, _srv_cache_ts
    if _srv_cache is not None and (time.monotonic() - _srv_cache_ts) < _SRV_CACHE_TTL_S:
        logger.debug("monitoring/server cache hit")
        return _srv_cache
    metrics: dict[str, Any] = {
        "hostname": platform.node(),
        "platform": platform.system(),
        "platform_version": platform.release(),
        "architecture": platform.machine(),
        "cpu": None,
        "memory": None,
        "disk": None,
        "network": None,
        "uptime_seconds": None,
        "uptime_human": None,
        "load_average": None,
        "process_count": None,
        "status": "unknown",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }

    try:
        import psutil

        # CPU — interval=None reads the last sample cached by the OS instead
        # of blocking the thread for 0.5 s. psutil already refreshes this
        # counter in the background after the first call, so the value is
        # still accurate (usually < 1 s stale).
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        metrics["cpu"] = {
            "usage_percent": round(cpu_percent, 1),
            "core_count": cpu_count,
            "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
        }

        # Memory
        mem = psutil.virtual_memory()
        metrics["memory"] = {
            "usage_percent": round(mem.percent, 1),
            "total_mb": round(mem.total / 1_048_576, 0),
            "used_mb": round(mem.used / 1_048_576, 0),
            "available_mb": round(mem.available / 1_048_576, 0),
        }

        # Disk (root partition)
        disk = psutil.disk_usage("/")
        metrics["disk"] = {
            "usage_percent": round(disk.percent, 1),
            "total_gb": round(disk.total / 1_073_741_824, 1),
            "used_gb": round(disk.used / 1_073_741_824, 1),
            "free_gb": round(disk.free / 1_073_741_824, 1),
        }

        # Network (cumulative counters)
        net = psutil.net_io_counters()
        metrics["network"] = {
            "bytes_sent_total": net.bytes_sent,
            "bytes_recv_total": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errors_in": net.errin,
            "errors_out": net.errout,
        }

        # Uptime
        boot_time = psutil.boot_time()
        uptime_sec = (datetime.now().timestamp() - boot_time)
        metrics["uptime_seconds"] = int(uptime_sec)
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        minutes = int((uptime_sec % 3600) // 60)
        metrics["uptime_human"] = f"{days}d {hours}h {minutes}m"

        # Load average (Unix only)
        try:
            load = os.getloadavg()
            metrics["load_average"] = {"1min": round(load[0], 2), "5min": round(load[1], 2), "15min": round(load[2], 2)}
        except (AttributeError, OSError):
            metrics["load_average"] = None  # Windows

        # Process count
        metrics["process_count"] = len(psutil.pids())

        metrics["status"] = "healthy" if cpu_percent < 90 and mem.percent < 90 and disk.percent < 90 else "warning"

    except ImportError:
        metrics["status"] = "psutil_unavailable"
        metrics["error"] = "psutil library not installed — install it to get real server metrics"
    except Exception as exc:
        metrics["status"] = "error"
        metrics["error"] = str(exc)
        logger.warning("Server metrics collection failed: %s", exc)

    _srv_cache = metrics
    _srv_cache_ts = time.monotonic()
    return metrics


# ─────────────────────────────────────────────────────────────
# SECURITY EVENTS — Real sources from app audit log + auth failures
# ─────────────────────────────────────────────────────────────

@router.get("/security")
def get_security_events(_: CurrentUser = Depends(get_current_user)):
    """
    Returns real security events from the application's own audit trail.
    Cached for 60 s — security events don't change faster than that.
    """
    global _sec_cache, _sec_cache_ts
    if _sec_cache is not None and (time.monotonic() - _sec_cache_ts) < _SEC_CACHE_TTL_S:
        logger.debug("monitoring/security cache hit")
        return _sec_cache
    events = []
    summary = {
        "total_events": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "threat_level": "LOW",
        "failed_login_attempts_24h": 0,
        "active_alerts": 0,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "data_sources": [],
    }

    try:
        engine = get_app_engine()

        # Run all three queries inside one connection — avoids 3 round-trips
        with engine.connect() as conn:

            # 1. Security alerts
            try:
                alert_rows = conn.execute(text(
                    """SELECT id, title, description, severity, category,
                              created_at, status, recommended_action
                       FROM alerts
                       WHERE category IN ('security','authentication',
                                         'access_control','network','system')
                          OR severity IN ('critical','high')
                       ORDER BY created_at DESC
                       LIMIT 50"""
                )).mappings().all()

                if alert_rows:
                    summary["data_sources"].append("alerts_table")
                    for row in alert_rows:
                        row = dict(row)
                        sev = (row.get("severity") or "medium").lower()
                        events.append({
                            "id": str(row.get("id", "")),
                            "timestamp": row["created_at"].isoformat()
                                if hasattr(row.get("created_at"), "isoformat")
                                else str(row.get("created_at", "")),
                            "severity": sev.capitalize(),
                            "category": row.get("category", "system"),
                            "event": row.get("title", "Security Event"),
                            "description": row.get("description", ""),
                            "source": "ERAOP Alert Engine",
                            "status": row.get("status", "active"),
                            "recommended_action": row.get("recommended_action", ""),
                        })
                        if sev == "critical":
                            summary["critical_count"] += 1
                        elif sev == "high":
                            summary["high_count"] += 1
                        elif sev == "medium":
                            summary["medium_count"] += 1
                        else:
                            summary["low_count"] += 1
            except Exception:
                pass

            # 2. Failed login count
            try:
                fail_row = conn.execute(text(
                    """SELECT COUNT(*) AS cnt FROM logs
                       WHERE event_type = 'auth_failure'
                         AND created_at > NOW() - INTERVAL '24 hours'"""
                )).mappings().first()
                if fail_row:
                    summary["data_sources"].append("auth_logs")
                    cnt = int(fail_row["cnt"] or 0)
                    summary["failed_login_attempts_24h"] = cnt
                    if cnt > 0:
                        events.insert(0, {
                            "id": "auth_fail_summary",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "severity": "High" if cnt > 5 else "Medium",
                            "category": "authentication",
                            "event": f"{cnt} failed login attempts in last 24h",
                            "description": "Multiple authentication failures detected from application login endpoint",
                            "source": "Auth System",
                            "status": "active",
                            "recommended_action": "Review login activity and consider account lockout policies",
                        })
            except Exception:
                pass

            # 3. Active alert count
            try:
                active_row = conn.execute(text(
                    "SELECT COUNT(*) AS cnt FROM alerts WHERE status = 'active'"
                )).mappings().first()
                if active_row:
                    summary["active_alerts"] = int(active_row["cnt"] or 0)
            except Exception:
                pass

    except Exception as exc:
        logger.warning("Security metrics collection failed: %s", exc)
        summary["data_sources"].append(f"error: {exc}")

    # Determine overall threat level
    summary["total_events"] = len(events)
    if summary["critical_count"] > 0:
        summary["threat_level"] = "CRITICAL"
    elif summary["high_count"] > 2 or summary["failed_login_attempts_24h"] > 10:
        summary["threat_level"] = "HIGH"
    elif summary["high_count"] > 0 or summary["medium_count"] > 5 or summary["failed_login_attempts_24h"] > 3:
        summary["threat_level"] = "ELEVATED"
    else:
        summary["threat_level"] = "LOW"

    result = {"events": events, "summary": summary}
    _sec_cache = result
    _sec_cache_ts = time.monotonic()
    return result
# NOTIFICATIONS — aggregated feed for the notification bell
# Combines real alerts + server status + security events into
# the format the frontend notification bell expects.
# The frontend Ki() calls /webhook/notifications-api (n8n) which
# is often not deployed. This endpoint is the real backend source.
# ─────────────────────────────────────────────────────────────

@router.get("/notifications")
def get_notifications(_: CurrentUser = Depends(get_current_user)):
    """
    Returns a unified list of system notifications sourced entirely from
    the live backend: DB alerts, server health, and security events.

    The frontend notification bell calls /webhook/notifications-api (n8n)
    which is unavailable in most deployments. This endpoint provides the
    same data structure so the frontend can fall back to it.
    """
    global _notif_cache, _notif_cache_ts
    if _notif_cache is not None and (time.monotonic() - _notif_cache_ts) < _NOTIF_CACHE_TTL_S:
        logger.debug("monitoring/notifications cache hit")
        return _notif_cache

    notifications: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Real alerts from the app database
    try:
        engine = get_app_engine()
        with engine.connect() as conn:
            rows = conn.execute(text(
                """SELECT id, title, description, severity, category, created_at
                   FROM alerts
                   ORDER BY created_at DESC
                   LIMIT 30"""
            )).mappings().all()
            for r in rows:
                r = dict(r)
                sev = (r.get("severity") or "medium").lower()
                title = r.get("title") or "System Alert"
                ts = r.get("created_at")
                notifications.append({
                    "id": str(r.get("id", "")),
                    "title": title,
                    "message": r.get("description") or title,
                    "type": "critical" if sev == "critical" else
                            "warning" if sev == "high" else "info",
                    "severity": sev,
                    "category": r.get("category", "system"),
                    "created_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts or now_iso),
                    "is_read": False,
                    "source": "Alert Engine",
                })
    except Exception as exc:
        logger.debug("Notifications: alerts query skipped: %s", exc)

    # 2. Server health notification (from psutil — no DB round-trip)
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        if cpu > 85 or mem > 85 or disk > 85:
            notifications.insert(0, {
                "id": "server_health_warn",
                "title": "Server Resource Warning",
                "message": f"CPU {cpu:.0f}% · RAM {mem:.0f}% · Disk {disk:.0f}% — high utilization detected.",
                "type": "critical" if cpu > 95 or mem > 95 else "warning",
                "severity": "high" if cpu > 95 or mem > 95 else "medium",
                "category": "server",
                "created_at": now_iso,
                "is_read": False,
                "source": "Server Monitor",
            })
        else:
            notifications.append({
                "id": "server_health_ok",
                "title": "Server Health Normal",
                "message": f"CPU {cpu:.0f}% · RAM {mem:.0f}% · Disk {disk:.0f}% — all within normal range.",
                "type": "info",
                "severity": "low",
                "category": "server",
                "created_at": now_iso,
                "is_read": True,
                "source": "Server Monitor",
            })
    except Exception:
        pass

    # 3. Database connectivity notification
    try:
        engine = get_target_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        notifications.append({
            "id": "db_connected",
            "title": "Database Connected",
            "message": "Target Supabase database is reachable and responding.",
            "type": "info",
            "severity": "low",
            "category": "database",
            "created_at": now_iso,
            "is_read": True,
            "source": "Database Monitor",
        })
    except Exception as exc:
        notifications.insert(0, {
            "id": "db_error",
            "title": "Database Connection Error",
            "message": f"Cannot reach target database: {str(exc)[:120]}",
            "type": "critical",
            "severity": "critical",
            "category": "database",
            "created_at": now_iso,
            "is_read": False,
            "source": "Database Monitor",
        })

    _notif_cache = notifications
    _notif_cache_ts = time.monotonic()
    return notifications
