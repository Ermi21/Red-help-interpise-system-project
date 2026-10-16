"""Declarative base for the APPLICATION database ORM models.

These models describe tables this backend owns and writes to (users,
conversations, cached documentation, alerts). They have nothing to do with
the read-only target/company database, which is never modeled as ORM
classes — it is only ever queried through query_executor with validated
raw SQL, since its schema is unknown ahead of time and discovered at
runtime.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
