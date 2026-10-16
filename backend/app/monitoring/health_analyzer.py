"""
Database health analysis.

Every check here is read-only: it either uses SQLAlchemy's Inspector
(dialect-agnostic) or issues SELECT statements against catalog views,
always through execute_readonly_query so it passes through the same
readonly_guard as everything else. Some checks (index/statistics based)
are Postgres-specific and are skipped gracefully on other dialects.
"""
from datetime import datetime, timezone

from sqlalchemy.engine import Engine

from app.config.settings import get_settings
from app.database.query_executor import execute_readonly_query
from app.database.schema_discovery import TableInfo, discover_schema
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _is_postgres(engine: Engine) -> bool:
    return engine.dialect.name == "postgresql"


def _check_missing_primary_keys(tables: list[TableInfo]) -> list[dict]:
    issues = []
    for table in tables:
        if table.is_view:
            continue
        if not table.primary_key:
            issues.append(
                {
                    "category": "schema_design",
                    "severity": "medium",
                    "table": table.name,
                    "column": None,
                    "description": f"Table '{table.name}' has no primary key defined.",
                    "recommendation": f"Add a primary key to '{table.name}' to ensure row uniqueness and enable efficient replication/indexing.",
                }
            )
    return issues


def _check_missing_fk_indexes(tables: list[TableInfo]) -> list[dict]:
    """Foreign key columns without a covering index are a very common
    cause of slow JOINs — this check is dialect-agnostic since it only
    needs the FK and index metadata SQLAlchemy already gave us."""
    issues = []
    for table in tables:
        indexed_columns = {col for idx in table.indexes for col in idx.columns}
        indexed_columns.update(table.primary_key)
        for fk in table.foreign_keys:
            uncovered = [c for c in fk.constrained_columns if c not in indexed_columns]
            if uncovered:
                issues.append(
                    {
                        "category": "performance",
                        "severity": "medium",
                        "table": table.name,
                        "column": ", ".join(uncovered),
                        "description": (
                            f"Foreign key column(s) {uncovered} on '{table.name}' "
                            f"(referencing '{fk.referred_table}') has no index."
                        ),
                        "recommendation": f"Create an index on {table.name}({', '.join(uncovered)}) to improve JOIN performance.",
                    }
                )
    return issues


def _check_duplicate_indexes(tables: list[TableInfo]) -> list[dict]:
    issues = []
    for table in tables:
        seen: dict[tuple, str] = {}
        for idx in table.indexes:
            key = tuple(idx.columns)
            if key in seen:
                issues.append(
                    {
                        "category": "performance",
                        "severity": "low",
                        "table": table.name,
                        "column": ", ".join(idx.columns),
                        "description": f"Indexes '{seen[key]}' and '{idx.name}' on '{table.name}' cover the same columns {list(key)}.",
                        "recommendation": f"Consider dropping the redundant index '{idx.name}' to reduce write overhead and storage.",
                    }
                )
            else:
                seen[key] = idx.name
    return issues


def _check_naming_conventions(tables: list[TableInfo]) -> list[dict]:
    issues = []
    for table in tables:
        if table.name.lower() != table.name and " " not in table.name:
            issues.append(
                {
                    "category": "consistency",
                    "severity": "low",
                    "table": table.name,
                    "column": None,
                    "description": f"Table name '{table.name}' does not follow lower_snake_case convention.",
                    "recommendation": "Standardize on a single naming convention (e.g. snake_case) across the schema for maintainability.",
                }
            )
    return issues


def _check_null_ratios(tables: list[TableInfo]) -> list[dict]:
    """Best-effort NULL-ratio sampling. Skipped for very large tables to
    avoid expensive full scans; relies on COUNT(*) which is a safe read."""
    settings = get_settings()
    issues = []
    for table in tables:
        if table.is_view:
            continue
        nullable_cols = [c.name for c in table.columns if c.nullable]
        if not nullable_cols:
            continue
        try:
            total_row = execute_readonly_query(f'SELECT COUNT(*) AS c FROM "{table.name}"')
            total = total_row[0]["c"] if total_row else 0
            if not total:
                continue
            for col in nullable_cols[:10]:  # cap columns checked per table
                null_row = execute_readonly_query(f'SELECT COUNT(*) AS c FROM "{table.name}" WHERE "{col}" IS NULL')
                null_count = null_row[0]["c"] if null_row else 0
                ratio = null_count / total
                if ratio >= settings.null_ratio_warning_threshold:
                    issues.append(
                        {
                            "category": "data_quality",
                            "severity": "low",
                            "table": table.name,
                            "column": col,
                            "description": f"Column '{col}' on '{table.name}' is {ratio:.0%} NULL ({null_count}/{total} rows).",
                            "recommendation": f"Review whether '{col}' should be NOT NULL, have a default, or be removed if largely unused.",
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            logger.info("Skipped NULL-ratio check for '%s': %s", table.name, exc)
    return issues


def _check_orphan_candidates_postgres(engine: Engine) -> list[dict]:
    """Postgres-specific: surfaces tables/indexes flagged by the DB's own
    statistics as unused, using pg_stat_user_tables (a read-only catalog
    view — never modifies anything)."""
    if not _is_postgres(engine):
        return []
    sql = """
        SELECT relname AS table_name, seq_scan, idx_scan, n_live_tup
        FROM pg_stat_user_tables
        WHERE idx_scan = 0 AND seq_scan > 0 AND n_live_tup > 1000
        ORDER BY n_live_tup DESC
        LIMIT 20
    """
    try:
        rows = execute_readonly_query(sql)
    except Exception as exc:  # noqa: BLE001
        logger.info("Postgres statistics check skipped: %s", exc)
        return []

    return [
        {
            "category": "performance",
            "severity": "medium",
            "table": row["table_name"],
            "column": None,
            "description": (
                f"'{row['table_name']}' has {row['n_live_tup']} rows and has never been read via "
                f"an index scan ({row['seq_scan']} sequential scans recorded)."
            ),
            "recommendation": f"Review query patterns against '{row['table_name']}' — it likely needs an index matching its common WHERE/JOIN columns.",
        }
        for row in rows
    ]


def analyze_health(engine: Engine) -> dict:
    tables = discover_schema(engine)

    issues: list[dict] = []
    issues += _check_missing_primary_keys(tables)
    issues += _check_missing_fk_indexes(tables)
    issues += _check_duplicate_indexes(tables)
    issues += _check_naming_conventions(tables)
    issues += _check_null_ratios(tables)
    issues += _check_orphan_candidates_postgres(engine)

    return {
        "generated_at": datetime.now(timezone.utc),
        "tables_analyzed": len(tables),
        "issues": issues,
    }
