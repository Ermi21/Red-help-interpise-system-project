"""
Read-only SQL guard.

This module is the single source of truth for "is this SQL statement safe
to run against the protected company database". It is deliberately
conservative: anything it cannot confidently classify as a safe read is
rejected.

Defense in depth — this guard is applied at THREE layers:
  1. Here, before any statement is handed to SQLAlchemy (app.database.query_executor)
     via the strict validate_sql() allow-list.
  2. As a SQLAlchemy `before_cursor_execute` event on the target engine
     (app.database.connection), via the more permissive
     check_connection_level_safety(), so even a future code path that
     forgets to call validate_sql directly still gets checked — without
     breaking SQLAlchemy's own internal reflection queries.
  3. At the database role level — the configured DB user should itself only
     have SELECT privileges. This module assumes that grant may be
     misconfigured and does not rely on it alone.
"""
import re

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import DDL, DML

from app.utils.exceptions import UnsafeSQLError

# Statement types that are always allowed.
_ALLOWED_DML = {"SELECT"}

# Non-DML keywords that represent safe, read-only introspection statements.
_ALLOWED_LEADING_KEYWORDS = {
    "SELECT",
    "SHOW",
    "EXPLAIN",
    "DESCRIBE",
    "DESC",
    "WITH",  # CTEs — validated further below to ensure they terminate in a SELECT
}

# Keywords that always represent a real mutation or dangerous side effect.
# No legitimate reflection/introspection query — ours or SQLAlchemy's own
# internal dialect machinery — ever needs these, so they are blocked at
# BOTH layers (the strict validator below, and the permissive
# connection-level check used by the engine event listener).
_HARD_MUTATION_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "REPLACE",
    "CALL",
    "EXEC",
    "EXECUTE",
    "COPY",
    "VACUUM",
    "REINDEX",
    "LOCK",
    "ATTACH",
    "DETACH",
    "INTO",  # blocks `SELECT ... INTO new_table`
}

# Session/config-control keywords. These carry real risk in arbitrary,
# user- or LLM-supplied SQL (e.g. Postgres's `SET session_replication_role
# = replica` is a known trick to disable triggers/FK checks; SQLite's
# `PRAGMA writable_schema` can be used to tamper with the schema table
# directly) — so the strict validator blocks them. BUT SQLAlchemy's own
# dialect/reflection internals legitimately issue these (e.g. SQLite's
# Inspector runs `PRAGMA table_info(...)` to list columns), so the
# permissive connection-level check does NOT block them; that layer only
# exists to catch actual mutations that slip through some future code path
# that forgot to call validate_sql() explicitly.
_SESSION_CONTROL_KEYWORDS = {"SET", "RESET", "PRAGMA"}

_FORBIDDEN_KEYWORDS = _HARD_MUTATION_KEYWORDS | _SESSION_CONTROL_KEYWORDS

_MAX_STATEMENTS = 1


def _leading_keyword(statement: Statement) -> str | None:
    for token in statement.tokens:
        if token.is_whitespace or token.ttype in (sqlparse.tokens.Comment,):
            continue
        return token.value.upper()
    return None


def validate_sql(raw_sql: str) -> str:
    """Validate that `raw_sql` contains exactly one safe, read-only statement.

    Returns the trimmed SQL on success. Raises UnsafeSQLError on any
    statement this guard cannot confidently classify as safe.
    """
    if not raw_sql or not raw_sql.strip():
        raise UnsafeSQLError("Empty SQL statement.")

    cleaned = raw_sql.strip().rstrip(";")

    # Reject stacked/multi-statement queries (a classic SQL-injection vector:
    # "SELECT 1; DROP TABLE users;"). sqlparse.split is used rather than a
    # naive `;` count because semicolons can legally appear inside string
    # literals.
    statements = [s for s in sqlparse.split(raw_sql) if s.strip()]
    if len(statements) > _MAX_STATEMENTS:
        raise UnsafeSQLError(
            "Multiple SQL statements detected in a single request; only one "
            "read statement is permitted per query.",
            details={"statement_count": len(statements)},
        )

    parsed = sqlparse.parse(cleaned)
    if not parsed:
        raise UnsafeSQLError("Could not parse SQL statement.")
    statement = parsed[0]

    leading = _leading_keyword(statement)
    if leading is None or leading.upper() not in _ALLOWED_LEADING_KEYWORDS:
        raise UnsafeSQLError(
            f"Statement type '{leading}' is not permitted. Only SELECT / "
            f"SHOW / EXPLAIN / DESCRIBE statements are allowed.",
            details={"leading_keyword": leading},
        )

    # Keyword blacklist scan across every token, not just the leading one —
    # this catches things like CTEs or subqueries smuggling in a write, and
    # multi-word DDL/DML tokens sqlparse may classify differently across
    # dialects.
    upper_sql = cleaned.upper()
    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise UnsafeSQLError(
                f"Forbidden keyword '{keyword}' detected in query.",
                details={"forbidden_keyword": keyword},
            )

    # Belt-and-suspenders: explicitly reject any token sqlparse itself
    # classifies as DDL, or DML other than SELECT.
    for token in statement.flatten():
        if token.ttype is DDL:
            raise UnsafeSQLError("DDL statement detected and rejected.")
        if token.ttype is DML and token.value.upper() not in _ALLOWED_DML:
            raise UnsafeSQLError(f"Disallowed DML statement: {token.value}")

    return cleaned


def is_safe(raw_sql: str) -> bool:
    try:
        validate_sql(raw_sql)
        return True
    except UnsafeSQLError:
        return False


def check_connection_level_safety(raw_sql: str) -> None:
    """Permissive, connection-level defense-in-depth check.

    Unlike validate_sql (an allow-list that only permits SELECT / SHOW /
    EXPLAIN / DESCRIBE), this only blocks genuine mutations. It exists so
    the `before_cursor_execute` engine listener in app.database.connection
    can catch a future code path that forgot to call validate_sql, WITHOUT
    also breaking SQLAlchemy's own internal reflection queries — e.g. the
    SQLite dialect's Inspector runs `PRAGMA table_info(...)` under the
    hood, which is a read-only introspection query but isn't a SELECT.

    Raises UnsafeSQLError if the statement contains a hard mutation
    keyword or is classified as DDL/non-SELECT DML by sqlparse.
    """
    if not raw_sql or not raw_sql.strip():
        return

    upper_sql = raw_sql.upper()
    for keyword in _HARD_MUTATION_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise UnsafeSQLError(
                f"Forbidden keyword '{keyword}' detected in query executed against the target database.",
                details={"forbidden_keyword": keyword},
            )

    try:
        parsed = sqlparse.parse(raw_sql.strip().rstrip(";"))
    except Exception:  # noqa: BLE001
        # If sqlparse itself can't handle the statement (e.g. an unusual
        # dialect-specific PRAGMA form), fall back to the keyword scan
        # above rather than blocking a legitimate internal query.
        return
    if not parsed:
        return

    for token in parsed[0].flatten():
        if token.ttype is DDL:
            raise UnsafeSQLError("DDL statement detected and rejected.")
        if token.ttype is DML and token.value.upper() not in _ALLOWED_DML:
            raise UnsafeSQLError(f"Disallowed DML statement: {token.value}")


def enforce_row_limit(raw_sql: str, max_rows: int) -> str:
    """Append a LIMIT clause if the query doesn't already have one.

    This is a pragmatic safety net to stop a runaway SELECT from returning
    (or an LLM-authored query from requesting) an unbounded result set. It
    is intentionally simple — if a LIMIT is already present we leave the
    query untouched rather than trying to rewrite it.
    """
    if re.search(r"\bLIMIT\s+\d+\b", raw_sql, re.IGNORECASE):
        return raw_sql
    return f"{raw_sql.rstrip()} LIMIT {max_rows}"
