"""
index_schema.py  —  Scan the TARGET database (read-only) and populate
ChromaDB with schema documentation so the RAG pipeline can retrieve
relevant table descriptions during inference.

Run inside the backend container:
    python /app/scripts/index_schema.py

Or from the host:
    docker compose exec backend python /app/scripts/index_schema.py
"""
import sys
import os

# Add the /app directory to sys.path so app.* imports work
sys.path.insert(0, "/app")

import sqlite3
from sqlalchemy import create_engine, inspect, text
from langchain_core.documents import Document

from app.config.settings import get_settings
from app.embeddings.vector_store import VectorStoreManager
from app.chatbot.prompt_templates import build_schema_doc_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_sqlite_tables(db_path: str) -> list[dict]:
    """Introspect a SQLite file directly and return table schemas."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_names = [row[0] for row in cur.fetchall()]

    tables = []
    for tname in table_names:
        cur.execute(f"PRAGMA table_info({tname})")
        cols = cur.fetchall()  # (cid, name, type, notnull, dflt, pk)
        col_list = [f"{col[1]} {col[2]}{'  NOT NULL' if col[3] else ''}{'  PK' if col[5] else ''}" for col in cols]

        cur.execute(f"PRAGMA foreign_key_list({tname})")
        fks = cur.fetchall()
        fk_list = [f"{row[3]} -> {row[2]}.{row[4]}" for row in fks] if fks else []

        pk_cols = [col[1] for col in cols if col[5]]

        tables.append({
            "name": tname,
            "columns": col_list,
            "primary_key": ", ".join(pk_cols) if pk_cols else "—",
            "foreign_keys": ", ".join(fk_list) if fk_list else "—",
        })

    conn.close()
    return tables


def build_doc_text(table: dict) -> str:
    """Build a rich documentation string for a table."""
    col_text = "\n  ".join(table["columns"])
    return (
        f"Table: {table['name']}\n"
        f"Columns:\n  {col_text}\n"
        f"Primary Key: {table['primary_key']}\n"
        f"Foreign Keys: {table['foreign_keys']}\n"
    )


def main():
    settings = get_settings()
    target_url = settings.target_db_url or ""

    print(f"Target DB URL: {target_url[:60]}...")

    tables = []

    if target_url.startswith("sqlite:///"):
        # Direct SQLite introspection
        db_path = target_url.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            print(f"ERROR: SQLite file not found at {db_path}")
            sys.exit(1)
        print(f"Introspecting SQLite at {db_path}")
        tables = get_sqlite_tables(db_path)
    else:
        # Generic SQLAlchemy introspection for PostgreSQL / MySQL
        engine = create_engine(target_url)
        try:
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            print(f"Found {len(table_names)} tables")
            for tname in table_names:
                cols = inspector.get_columns(tname)
                pks = inspector.get_pk_constraint(tname).get("constrained_columns", [])
                fks = inspector.get_foreign_keys(tname)
                col_list = [f"{c['name']} {c['type']}" for c in cols]
                fk_list = [f"{f['constrained_columns']} -> {f['referred_table']}.{f['referred_columns']}" for f in fks]
                tables.append({
                    "name": tname,
                    "columns": col_list,
                    "primary_key": ", ".join(pks) or "—",
                    "foreign_keys": ", ".join(fk_list) or "—",
                })
        finally:
            engine.dispose()

    if not tables:
        print("No tables found in target database. Nothing to index.")
        sys.exit(0)

    print(f"\nFound {len(tables)} tables: {[t['name'] for t in tables]}\n")

    vs = VectorStoreManager()

    documents = []
    for table in tables:
        # Clear stale chunks for this table
        vs.delete_by_table(table["name"])

        doc_text = build_doc_text(table)
        col_str = "\n".join(table["columns"])
        documents.append(Document(
            page_content=doc_text,
            metadata={
                "table": table["name"],
                "columns": col_str,
                "primary_key": table["primary_key"],
                "foreign_keys": table["foreign_keys"],
            }
        ))
        print(f"  ✓ Prepared: {table['name']} ({len(table['columns'])} columns)")

    count = vs.add_documents(documents)
    print(f"\n✅ Indexed {count} table documents into ChromaDB vector store.")

    # Verify
    total = vs.store._collection.count()
    print(f"📊 Total documents in collection: {total}")


if __name__ == "__main__":
    main()
