"""
Schema discovery.

Uses SQLAlchemy's dialect-agnostic Inspector to enumerate tables, columns,
keys, indexes and views on the target database. This never executes raw
SQL directly for the core inspection (SQLAlchemy issues the appropriate
catalog/information_schema queries for whichever backend is configured),
so it works across Postgres, MySQL, SQL Server, etc.

Stored procedure discovery IS backend-specific (there is no portable
SQLAlchemy API for it) and is implemented for Postgres with a safe,
read-only information_schema query, gated through the same readonly_guard
as everything else.
"""
from dataclasses import dataclass, field

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database.query_executor import execute_readonly_query
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    default: str | None
    is_primary_key: bool


@dataclass
class ForeignKeyInfo:
    constrained_columns: list[str]
    referred_table: str
    referred_columns: list[str]


@dataclass
class IndexInfo:
    name: str
    columns: list[str]
    unique: bool


@dataclass
class TableInfo:
    name: str
    schema: str | None
    columns: list[ColumnInfo] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)
    is_view: bool = False


def discover_schema(engine: Engine, schema: str | None = None) -> list[TableInfo]:
    """Introspect every table and view visible to the read-only DB user."""
    inspector = inspect(engine)
    tables: list[TableInfo] = []

    table_names = inspector.get_table_names(schema=schema)
    view_names = set(inspector.get_view_names(schema=schema))

    for name in [*table_names, *view_names]:
        try:
            pk_constraint = inspector.get_pk_constraint(name, schema=schema)
            pk_columns = set(pk_constraint.get("constrained_columns") or [])

            columns = [
                ColumnInfo(
                    name=col["name"],
                    type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    default=str(col["default"]) if col.get("default") is not None else None,
                    is_primary_key=col["name"] in pk_columns,
                )
                for col in inspector.get_columns(name, schema=schema)
            ]

            foreign_keys = [
                ForeignKeyInfo(
                    constrained_columns=fk["constrained_columns"],
                    referred_table=fk["referred_table"],
                    referred_columns=fk["referred_columns"],
                )
                for fk in inspector.get_foreign_keys(name, schema=schema)
            ]

            indexes = [
                IndexInfo(name=idx["name"] or "", columns=idx["column_names"] or [], unique=idx.get("unique", False))
                for idx in inspector.get_indexes(name, schema=schema)
            ]

            tables.append(
                TableInfo(
                    name=name,
                    schema=schema,
                    columns=columns,
                    primary_key=list(pk_columns),
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                    is_view=name in view_names,
                )
            )
        except Exception as exc:  # noqa: BLE001
            # A single misbehaving table/view (e.g. a broken view definition)
            # should never take down the whole discovery run.
            logger.warning("Skipped introspection for '%s': %s", name, exc)

    logger.info("Schema discovery complete: %d tables/views found", len(tables))
    return tables


def discover_stored_procedures_postgres() -> list[dict]:
    """Best-effort, read-only enumeration of stored procedures/functions on
    Postgres. Returns an empty list on any other dialect or on failure."""
    sql = """
        SELECT routine_name, routine_type, data_type AS return_type
        FROM information_schema.routines
        WHERE routine_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY routine_name
        LIMIT 500
    """
    try:
        rows = execute_readonly_query(sql)
        return rows
    except Exception as exc:  # noqa: BLE001
        logger.info("Stored procedure discovery skipped/unavailable: %s", exc)
        return []
