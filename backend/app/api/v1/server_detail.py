"""
Expanded Server Monitoring API.

Endpoints
---------
GET /server/metrics/history      — time-series CPU/RAM/disk (last N points)
GET /server/services             — health of API, DB, vector store, Groq, embeddings
GET /server/requests             — request rate, latency, error rate
GET /server/llm-usage            — token counts, cost, errors by day/hour
GET /server/logs                 — searchable, paginated application logs
GET /server/uptime               — uptime history timeline
"""
import os
import time as _time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, require_role
from app.auth.rbac import Role
from app.config.settings import get_settings
from app.database.connection import get_app_engine, get_target_engine
from app.models.llm_usage import LlmUsage
from app.models.system_metrics import SystemMetric
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/server", tags=["Server Detail"])

# ── Service health latency cache (probe each service at most once per 30 s) ──
_svc_cache: dict | None = None
_svc_cache_ts: float = 0.0
_SVC_CACHE_TTL = 30


# ── Metric history ─────────────────────────────────────────────────────────────

@router.get("/metrics/history")
def get_metrics_history(
    _: CurrentUser = Depends(get_current_user),
    points: int = Query(60, ge=1, le=1440),          # default last 60 samples = 15 min
):
    """Return the last `points` rows from system_metrics as time-series data."""
    from app.database.connection import app_session
    with app_session() as session:
        rows = session.execute(
            select(SystemMetric)
            .order_by(SystemMetric.collected_at.desc())
            .limit(points)
        ).scalars().all()

        series = [
            {
                "time": r.collected_at.isoformat() if r.collected_at else "",
                "cpu_percent": r.cpu_percent,
                "mem_percent": r.mem_percent,
                "disk_percent": r.disk_percent,
                "requests_total": r.requests_total,
                "requests_error": r.requests_error,
                "avg_latency_ms": r.avg_latency_ms,
            }
            for r in reversed(rows)
        ]

    return {
        "points": len(series),
        "series": series,
    }


# ── Service health cards ───────────────────────────────────────────────────────

@router.get("/services")
def get_service_health(_: CurrentUser = Depends(get_current_user)):
    """Probe each dependency and return status + latency."""
    global _svc_cache, _svc_cache_ts
    if _svc_cache is not None and (_time.monotonic() - _svc_cache_ts) < _SVC_CACHE_TTL:
        return _svc_cache

    services = []

    # 1. App DB
    services.append(_probe(
        name="App Database",
        fn=lambda: _ping_db(get_app_engine()),
    ))

    # 2. Target DB
    services.append(_probe(
        name="Target Database (Supabase)",
        fn=lambda: _ping_db(get_target_engine()),
    ))

    # 3. Vector store (ChromaDB)
    services.append(_probe(
        name="Vector Store (ChromaDB)",
        fn=_ping_chromadb,
    ))

    # 4. Groq API
    services.append(_probe(
        name="Groq LLM API",
        fn=_ping_groq,
    ))

    # 5. Ollama (optional embedding service)
    services.append(_probe(
        name="Ollama Embedding Service",
        fn=_ping_ollama,
    ))

    result = {"services": services, "checked_at": datetime.now(timezone.utc).isoformat()}
    _svc_cache = result
    _svc_cache_ts = _time.monotonic()
    return result


def _probe(name: str, fn) -> dict:
    start = _time.monotonic()
    try:
        fn()
        latency = round((_time.monotonic() - start) * 1000, 1)
        return {"name": name, "status": "healthy", "latency_ms": latency}
    except Exception as exc:
        latency = round((_time.monotonic() - start) * 1000, 1)
        return {"name": name, "status": "unhealthy", "latency_ms": latency, "error": str(exc)[:120]}


def _ping_db(engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _ping_chromadb() -> None:
    from app.embeddings.vector_store import get_vector_store
    vs = get_vector_store()
    vs.count()


def _ping_groq() -> None:
    settings = get_settings()
    import httpx
    resp = httpx.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        timeout=5,
    )
    resp.raise_for_status()


def _ping_ollama() -> None:
    settings = get_settings()
    import httpx
    httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3).raise_for_status()


# ── Request stats ──────────────────────────────────────────────────────────────

@router.get("/requests")
def get_request_stats(_: CurrentUser = Depends(get_current_user)):
    """Return aggregated request metrics from the last 5 minutes of samples."""
    from app.database.connection import app_session
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    with app_session() as session:
        row = session.execute(
            select(
                func.sum(SystemMetric.requests_total).label("total"),
                func.sum(SystemMetric.requests_error).label("errors"),
                func.avg(SystemMetric.avg_latency_ms).label("avg_ms"),
                func.count().label("samples"),
            ).where(SystemMetric.collected_at > cutoff)
        ).mappings().first()

    total  = int(row["total"] or 0)
    errors = int(row["errors"] or 0)
    avg_ms = round(float(row["avg_ms"] or 0), 1)
    samples = int(row["samples"] or 1)
    window_s = 300  # 5 minutes
    return {
        "window_seconds": window_s,
        "requests_total": total,
        "requests_per_minute": round(total / (window_s / 60), 1),
        "error_total": errors,
        "error_rate_pct": round((errors / total * 100) if total else 0, 1),
        "avg_latency_ms": avg_ms,
        "samples": samples,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


# ── LLM usage ──────────────────────────────────────────────────────────────────

# Groq pricing (approximate) per 1M tokens — update if pricing changes
_GROQ_INPUT_COST_PER_1M  = 0.05   # USD
_GROQ_OUTPUT_COST_PER_1M = 0.08

@router.get("/llm-usage")
def get_llm_usage(
    _: CurrentUser = Depends(get_current_user),
    hours: int = Query(24, ge=1, le=168),
):
    """Return LLM token usage and estimated cost for the last N hours."""
    from app.database.connection import app_session
    from sqlalchemy import case
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    with app_session() as session:
        row = session.execute(
            select(
                func.sum(LlmUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(LlmUsage.completion_tokens).label("completion_tokens"),
                func.sum(LlmUsage.total_tokens).label("total_tokens"),
                func.sum(LlmUsage.estimated_cost_usd).label("cost_usd"),
                func.count().label("calls"),
                func.sum(
                    case((LlmUsage.status != "success", 1), else_=0)
                ).label("errors"),
            ).where(LlmUsage.created_at > cutoff)
        ).mappings().first()

        # Per call-type breakdown
        by_type = session.execute(
            select(
                LlmUsage.call_type,
                func.count().label("calls"),
                func.sum(LlmUsage.total_tokens).label("tokens"),
                func.avg(LlmUsage.latency_ms).label("avg_ms"),
            ).where(LlmUsage.created_at > cutoff)
            .group_by(LlmUsage.call_type)
        ).mappings().all()

    return {
        "window_hours": hours,
        "total_calls": int(row["calls"] or 0),
        "prompt_tokens": int(row["prompt_tokens"] or 0),
        "completion_tokens": int(row["completion_tokens"] or 0),
        "total_tokens": int(row["total_tokens"] or 0),
        "estimated_cost_usd": round(float(row["cost_usd"] or 0), 4),
        "by_call_type": [
            {
                "call_type": r["call_type"],
                "calls": int(r["calls"]),
                "tokens": int(r["tokens"] or 0),
                "avg_latency_ms": round(float(r["avg_ms"] or 0), 1),
            }
            for r in by_type
        ],
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Application logs ───────────────────────────────────────────────────────────

@router.get("/logs")
def get_logs(
    _: CurrentUser = Depends(require_role(Role.ANALYST)),
    level: str | None = Query(None, description="ERROR | WARNING | INFO"),
    service: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    hours: int = Query(24, ge=1, le=168),
):
    """Read and filter the backend rotating log file."""
    import json as _json

    settings = get_settings()
    log_path = os.path.join(settings.log_dir, "backend.log")
    if not os.path.exists(log_path):
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    entries: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = _json.loads(line)
                except Exception:
                    continue
                # Filter by time
                ts_str = rec.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                except Exception:
                    pass
                # Filter by level
                if level and rec.get("level", "").upper() != level.upper():
                    continue
                # Filter by service
                if service and service.lower() not in rec.get("logger", "").lower():
                    continue
                # Text search
                if search:
                    combined = (rec.get("message", "") + " " + rec.get("logger", "")).lower()
                    if search.lower() not in combined:
                        continue
                entries.append({
                    "timestamp": rec.get("timestamp"),
                    "level": rec.get("level"),
                    "logger": rec.get("logger"),
                    "message": rec.get("message"),
                })
    except OSError as exc:
        logger.warning("Could not read log file: %s", exc)

    # Reverse so newest first, then paginate
    entries.reverse()
    total = len(entries)
    offset = (page - 1) * page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": entries[offset: offset + page_size],
    }
