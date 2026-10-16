"""
Seeds a small sample "company" database for local development.

Run against SQLite (zero setup) or a real Postgres instance you control —
this script uses its OWN plain SQLAlchemy engine (bypassing
app.database.connection's read-only guard entirely, since seeding
obviously requires writes) and should only ever be pointed at a local dev
database, never at a real read-only production target.

Usage:
    python scripts/seed_dev_data.py
    python scripts/seed_dev_data.py --url sqlite:///./company_dev.db
    python scripts/seed_dev_data.py --url postgresql+psycopg2://postgres:postgres@localhost:5432/company_dev
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text  # noqa: E402


DDL = [
    """CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        department_id INTEGER,
        notes TEXT
    )""",
]

SEED_ROWS = [
    "INSERT INTO departments (id, name) VALUES (1, 'Engineering')",
    "INSERT INTO departments (id, name) VALUES (2, 'Sales')",
    "INSERT INTO customers (id, name, email, department_id) VALUES (1, 'Alice', 'alice@example.com', 1)",
    "INSERT INTO customers (id, name, email, department_id) VALUES (2, 'Bob', 'bob@example.com', 1)",
    "INSERT INTO customers (id, name, email, department_id) VALUES (3, 'Carol', 'carol@example.com', 2)",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=os.environ.get("TARGET_DB_URL", "sqlite:///./company_dev.db"),
        help="SQLAlchemy URL of the database to seed (defaults to TARGET_DB_URL env var, or a local SQLite file).",
    )
    args = parser.parse_args()

    print(f"Seeding sample data into: {args.url}")
    engine = create_engine(args.url)

    with engine.begin() as conn:
        for stmt in DDL:
            conn.execute(text(stmt))

        existing = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        if existing:
            print(f"'customers' already has {existing} row(s) — skipping insert (safe to re-run).")
        else:
            for stmt in SEED_ROWS:
                conn.execute(text(stmt))
            print("Inserted sample departments/customers rows.")

    print("Done. Point TARGET_DB_URL at this database to try schema discovery, chat, and health checks.")


if __name__ == "__main__":
    main()
