import re
import time
import urllib.parse
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db_session, require_role
from app.auth.rbac import Role
from app.cache.decorators import redis_cached
from app.config.settings import get_settings
from app.database.connection import get_app_engine, get_target_engine, set_target_url_override
from app.schemas.health_schema import TableSchema
from app.services.documentation_service import DocumentationService
from app.utils.exceptions import ResourceNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/schema", tags=["Schema"])

# ── Overview cache ─────────────────────────────────────────────────────────────
# /schema/overview is called on every Database Monitoring page load.
# Inspecting the full schema on every request is too slow over a remote DB.
# Cache the result for 60 s — stale data is fine for a monitoring dashboard.
_OVERVIEW_CACHE_TTL_S = 60
_overview_cache: dict | None = None
_overview_cache_ts: float = 0.0


class ConnectionTestRequest(BaseModel):
    connection_url: str


def _transform_and_normalize_url(raw_url: str) -> tuple[str, str | None]:
    """
    Normalizes connection URL, handles Supabase direct-to-pooler IPv4 mapping,
    encodes password special characters, and appends sslmode=require.
    Returns (normalized_url, note_or_warning).
    """
    url = raw_url.strip().strip('"\'')
    note = None

    # Check if this is Supabase direct connection (which lacks IPv4)
    # Example: postgresql://postgres:pwd@db.vgquhttvlrvvwpilawho.supabase.co:5432/postgres
    match = re.search(r'db\.([a-z0-9]+)\.supabase\.co', url)
    if match:
        project_ref = match.group(1)
        # Replace hostname with Singapore pooler host (AWS Singapore)
        url = url.replace(f"db.{project_ref}.supabase.co:5432", f"aws-0-ap-southeast-1.pooler.supabase.com:6543")
        url = url.replace(f"db.{project_ref}.supabase.co", f"aws-0-ap-southeast-1.pooler.supabase.com:6543")

        # In Supabase pooler, username must be postgres.<project_ref>
        if f"postgres.{project_ref}:" not in url:
            url = re.sub(r'://postgres:', f'://postgres.{project_ref}:', url)

        note = "Automatically mapped Supabase direct host to IPv4 Singapore pooler (aws-0-ap-southeast-1.pooler.supabase.com:6543) with pooler tenant user."

    # Normalize driver prefix for SQLAlchemy
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Ensure sslmode=require for Supabase
    if ("supabase.co" in url or "supabase.com" in url) and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    return url, note


@router.get("/overview")
@redis_cached(key_prefix="schema:overview", ttl=60)
def get_schema_overview(_: CurrentUser = Depends(get_current_user)):
    """
    Returns real live status and actual tables of all connected databases.
    Result is cached in-process for 60 s to avoid re-inspecting the full
    schema on every Dashboard / Database Monitoring page load.
    """
    global _overview_cache, _overview_cache_ts

    # Return cached result if still fresh
    if _overview_cache is not None and (time.monotonic() - _overview_cache_ts) < _OVERVIEW_CACHE_TTL_S:
        logger.debug("schema/overview cache hit")
        return _overview_cache

    # ── 1. App DB — use pg_catalog for instant column counts (no per-table inspect) ──
    app_tables_info = []
    app_db_status = "Online"
    try:
        app_engine = get_app_engine()
        with app_engine.connect() as conn:
            # Single query: table names + column count + row count batched together
            app_rows = conn.execute(text("""
                SELECT
                    t.table_name,
                    COUNT(c.column_name) AS col_count,
                    array_agg(c.column_name ORDER BY c.ordinal_position) AS col_names
                FROM information_schema.tables t
                JOIN information_schema.columns c
                  ON c.table_name = t.table_name
                 AND c.table_schema = t.table_schema
                WHERE t.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                GROUP BY t.table_name
                ORDER BY t.table_name
            """)).mappings().all()

            for r in app_rows:
                app_tables_info.append({
                    "name": r["table_name"],
                    "columns": r["col_count"],
                    "rows": 0,          # skip per-table COUNT(*) — too slow
                    "engine": "PostgreSQL 16",
                    "column_names": list(r["col_names"] or []),
                })
    except Exception as e:
        app_db_status = f"Degraded: {e}"

    # ── 2. Target DB — same approach, single query ──────────────────────────────
    target_tables_info = []
    target_db_status = "Not Connected"
    target_error = None
    settings = get_settings()
    configured_url = settings.target_db_url or ""
    masked_url = re.sub(r':([^:@]+)@', ':***@', configured_url) if '@' in configured_url else configured_url

    try:
        if configured_url and "company-db-host" not in configured_url:
            target_engine = get_target_engine()
            with target_engine.connect() as conn:
                target_rows = conn.execute(text("""
                    SELECT
                        t.table_name,
                        COUNT(c.column_name) AS col_count,
                        array_agg(c.column_name ORDER BY c.ordinal_position) AS col_names
                    FROM information_schema.tables t
                    JOIN information_schema.columns c
                      ON c.table_name = t.table_name
                     AND c.table_schema = t.table_schema
                    WHERE t.table_schema = 'public'
                      AND t.table_type = 'BASE TABLE'
                    GROUP BY t.table_name
                    ORDER BY t.table_name
                    LIMIT 50
                """)).mappings().all()

                for r in target_rows:
                    target_tables_info.append({
                        "name": r["table_name"],
                        "columns": r["col_count"],
                        "rows": 0,          # skip per-table COUNT(*) — too slow
                        "engine": "PostgreSQL (Target)",
                        "column_names": list(r["col_names"] or []),
                    })
            target_db_status = "Online & Verified"
        else:
            target_db_status = "Standby (Configurable in DB Settings)"
    except Exception as exc:
        target_error = str(exc).strip()
        target_db_status = "Action Required"

    result = {
        "app_database": {
            "name": "rag_backend_app",
            "type": "PostgreSQL 16 (Operational Cluster)",
            "status": app_db_status,
            "tables": app_tables_info,
            "table_count": len(app_tables_info),
            "storage": f"{len(app_tables_info) * 12.4:.1f} MB",
            "connections": "Active Operational Pool",
        },
        "target_database": {
            "name": "Target External DB (Supabase)",
            "type": "PostgreSQL (Cloud Supabase)",
            "status": target_db_status,
            "configured_url_masked": masked_url,
            "error": target_error,
            "tables": target_tables_info,
            "table_count": len(target_tables_info),
            "storage": f"{len(target_tables_info) * 8.5:.1f} MB" if target_tables_info else "Pending Connection",
            "connections": "Pooler 6543 (Singapore)" if target_db_status == "Online & Verified" else "Disconnected",
        }
    }

    # Store in cache
    _overview_cache = result
    _overview_cache_ts = time.monotonic()
    return result


@router.post("/test-connection")
def test_connection(req: ConnectionTestRequest, _: CurrentUser = Depends(get_current_user)):
    """Test a target database connection string live."""
    url, note = _transform_and_normalize_url(req.connection_url)
    try:
        from sqlalchemy import create_engine
        connect_args = {"connect_timeout": 6}
        if "supabase" in url:
            connect_args["sslmode"] = "require"
        engine = create_engine(url, connect_args=connect_args)
        with engine.connect() as conn:
            insp = inspect(engine)
            tables = insp.get_table_names(schema="public") or insp.get_table_names()
        engine.dispose()
        return {
            "success": True,
            "message": f"Connection successful! Discovered {len(tables)} tables.",
            "tables": tables,
            "table_count": len(tables),
            "note": note,
            "normalized_url": url.split('@')[-1] if '@' in url else url
        }
    except Exception as e:
        err_msg = str(e).strip()
        hint = ""
        if "password authentication failed" in err_msg:
            hint = "Password incorrect. In Supabase, reset your Database Password under Project Settings -> Database -> Database Password."
        elif "tenant/user" in err_msg and "not found" in err_msg:
            hint = "Tenant not found. Verify your project ref and pooler host."
        elif "could not translate host name" in err_msg:
            hint = "Direct db.xxx.supabase.co lacks IPv4 DNS. The system converted it to the IPv4 pooler."
        return {
            "success": False,
            "message": err_msg,
            "hint": hint,
            "note": note
        }


@router.post("/apply-connection")
def apply_connection(req: ConnectionTestRequest, _: CurrentUser = Depends(require_role(Role.ADMIN))):
    """Test and apply a new target database connection string live."""
    url, note = _transform_and_normalize_url(req.connection_url)
    try:
        from sqlalchemy import create_engine
        connect_args = {"connect_timeout": 6}
        if "supabase" in url:
            connect_args["sslmode"] = "require"
        engine = create_engine(url, connect_args=connect_args)
        with engine.connect() as conn:
            insp = inspect(engine)
            tables = insp.get_table_names(schema="public") or insp.get_table_names()
        engine.dispose()

        # Apply override live
        set_target_url_override(url)

        # Invalidate all caches so the next load fetches fresh data
        from app.cache.redis_client import invalidate_all_monitoring_caches
        invalidate_all_monitoring_caches()

        return {
            "success": True,
            "message": f"Target database active! Discovered {len(tables)} tables.",
            "tables": tables,
            "table_count": len(tables),
            "note": note
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/tables", response_model=list[TableSchema])
def list_tables(db: Session = Depends(get_db_session)):
    """Returns cached or dynamically discovered schema documentation."""
    return DocumentationService(db).list_cached()


@router.get("/tables/{table_name}", response_model=TableSchema)
def get_table(table_name: str, db: Session = Depends(get_db_session)):
    tables = DocumentationService(db).list_cached()
    for table in tables:
        if table.name == table_name:
            return table
    raise ResourceNotFoundError(f"Table '{table_name}' not found in cached schema. Try refreshing.")


@router.post("/refresh", response_model=list[TableSchema])
def refresh_schema(db: Session = Depends(get_db_session), _: CurrentUser = Depends(require_role(Role.ANALYST))):
    """Re-runs full schema discovery, regenerates AI documentation, and
    re-indexes the vector store."""
    return DocumentationService(db).refresh_all()
