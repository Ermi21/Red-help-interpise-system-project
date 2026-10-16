"""
Query execution against the target (read-only) database.

Every call goes through readonly_guard.validate_sql before touching the
database. This is the ONLY module in the codebase that should execute
ad-hoc SQL strings against the target database.
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import get_settings
from app.database.connection import target_session
from app.database.readonly_guard import enforce_row_limit, validate_sql
from app.utils.exceptions import UnsafeSQLError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryExecutionError(Exception):
    pass


def execute_readonly_query(raw_sql: str, params: dict | None = None) -> list[dict]:
    """Validate and execute a single read-only SQL statement.

    Returns rows as a list of plain dicts (JSON-serializable). Raises
    UnsafeSQLError if the statement fails validation, or QueryExecutionError
    on any database-level failure (syntax error, timeout, etc.).
    """
    settings = get_settings()

    safe_sql = validate_sql(raw_sql)
    safe_sql = enforce_row_limit(safe_sql, settings.target_db_max_rows_returned)

    logger.info("Executing read-only query", extra={"sql": safe_sql})

    try:
        with target_session() as session:
            result = session.execute(text(safe_sql), params or {})
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return rows
    except UnsafeSQLError:
        raise
    except SQLAlchemyError as exc:
        logger.error("Query execution failed: %s", exc)
        raise QueryExecutionError(str(exc)) from exc
