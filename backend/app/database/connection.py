"""
Database connections.

This backend talks to TWO distinct databases and it is important they are
never confused with one another:

  * TARGET database — the company's database this whole system exists to
    analyze and answer questions about. Connected in READ-ONLY mode only.
    Enforced at three layers; see app.database.readonly_guard for details.

  * APP database — this backend's own operational store (users, chat
    history, cached schema docs, alerts). Normal read/write access. This is
    infrastructure we own, not customer data.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.database.readonly_guard import check_connection_level_safety
from app.utils.exceptions import DatabaseReadOnlyViolationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_target_engine: Engine | None = None
_app_engine: Engine | None = None
_TargetSession: sessionmaker | None = None
_AppSession: sessionmaker | None = None


def _install_readonly_guard(engine: Engine) -> None:
    """Attach a `before_cursor_execute` listener that re-validates every
    single statement sent through this engine, independent of whether the
    calling code already ran it through readonly_guard.validate_sql."""

    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def _guard(conn, cursor, statement, parameters, context, executemany):
        try:
            check_connection_level_safety(statement)
        except Exception as exc:  # noqa: BLE001 - re-raise as our domain exception
            logger.error("Blocked unsafe statement against target DB", extra={"statement": statement})
            raise DatabaseReadOnlyViolationError(
                "A non read-only statement was blocked before execution.",
                details={"reason": str(exc)},
            ) from exc
        return statement, parameters


_last_target_url: str | None = None
_target_url_override: str | None = None


def set_target_url_override(url: str):
    """Override target DB URL dynamically at runtime."""
    global _target_url_override
    _target_url_override = url.strip()
    reset_target_engine()


def reset_target_engine():
    """Dispose and reset the target engine (useful when TARGET_DB_URL is updated)."""
    global _target_engine, _TargetSession, _last_target_url
    if _target_engine is not None:
        try:
            _target_engine.dispose()
        except Exception:
            pass
    _target_engine = None
    _TargetSession = None
    _last_target_url = None


def get_target_engine() -> Engine:
    """Lazily build the engine for the protected, read-only target database."""
    global _target_engine, _TargetSession, _last_target_url, _target_url_override
    settings = get_settings()
    raw_url = (_target_url_override or settings.target_db_url or "").strip()

    # Rebuild engine if the configured URL changed
    if _target_engine is not None and _last_target_url != raw_url:
        reset_target_engine()

    if _target_engine is None:
        # Normalize protocol for synchronous SQLAlchemy + psycopg2
        url = raw_url
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

        # Automatically translate direct Supabase host (db.<ref>.supabase.co) to Singapore pooler
        # Direct Supabase endpoints have no IPv4 DNS in Docker networks.
        import re
        match = re.search(r'db\.([a-z0-9]+)\.supabase\.co', url)
        if match:
            project_ref = match.group(1)
            url = url.replace(f"db.{project_ref}.supabase.co:5432", f"aws-0-ap-southeast-1.pooler.supabase.com:6543")
            url = url.replace(f"db.{project_ref}.supabase.co", f"aws-0-ap-southeast-1.pooler.supabase.com:6543")
            if f"postgres.{project_ref}:" not in url:
                url = re.sub(r'://postgres:', f'://postgres.{project_ref}:', url)

        # Handle unencoded special characters in password (such as single quotes, caret, commas)
        # e.g. y8U3'w%5EPhR%2CpnVZ -> y8U3%27w%5EPhR%2CpnVZ
        if "'" in url:
            url = url.replace("'", "%27")

        # For Supabase & cloud PostgreSQL, ensure sslmode=require if not specified
        if ("supabase.co" in url or "supabase.com" in url) and "sslmode=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"

        connect_args = {}
        execution_options = {}

        is_postgres = url.startswith("postgresql")
        is_pooler = "pooler.supabase.com" in url or ":6543" in url

        if is_postgres:
            if not is_pooler:
                execution_options["postgresql_readonly"] = True
                connect_args["options"] = f"-c statement_timeout={settings.target_db_statement_timeout_ms}"
            else:
                # Supabase PgBouncer pooler (port 6543)
                connect_args["sslmode"] = "require"
        elif url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        engine_kwargs = {
            "pool_pre_ping": True,
            "execution_options": execution_options,
            "connect_args": connect_args,
        }
        if not url.startswith("sqlite"):
            engine_kwargs["pool_size"] = settings.target_db_pool_size

        try:
            _target_engine = create_engine(url, **engine_kwargs)
            _install_readonly_guard(_target_engine)
            _TargetSession = sessionmaker(bind=_target_engine, autoflush=False, autocommit=False)
            _last_target_url = raw_url
            safe_display = url.split('@')[-1] if '@' in url else url
            logger.info("Target (read-only) database engine initialized: %s", safe_display)
        except Exception as exc:
            logger.error("Failed to initialize target database engine with URL '%s': %s", raw_url, exc)
            raise

    return _target_engine


def get_app_engine() -> Engine:
    """Lazily build the engine for the app's own operational database."""
    global _app_engine, _AppSession
    if _app_engine is None:
        settings = get_settings()
        app_url = settings.app_db_url
        engine_kwargs = {"pool_pre_ping": True}
        connect_args = {}
        if app_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            engine_kwargs["connect_args"] = connect_args
        _app_engine = create_engine(app_url, **engine_kwargs)
        _AppSession = sessionmaker(bind=_app_engine, autoflush=False, autocommit=False)
        logger.info("Application database engine initialized")
    return _app_engine


@contextmanager
def target_session() -> Generator[Session, None, None]:
    get_target_engine()
    assert _TargetSession is not None
    session = _TargetSession()
    try:
        yield session
    finally:
        try:
            session.rollback()
        except Exception:
            pass
        session.close()


@contextmanager
def app_session() -> Generator[Session, None, None]:
    get_app_engine()
    assert _AppSession is not None
    session = _AppSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_app_db() -> Generator[Session, None, None]:
    """FastAPI dependency wrapper around app_session()."""
    with app_session() as session:
        yield session
