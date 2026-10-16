import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TableMetadata(Base):
    """Cached, AI-generated documentation for one table/view in the target
    database. Regenerated on schema refresh and re-embedded into the
    vector store."""

    __tablename__ = "table_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    schema_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_view: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_schema_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_generated_description: Mapped[str] = mapped_column(Text, default="")
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
