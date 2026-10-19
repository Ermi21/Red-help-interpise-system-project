"""
Unified notification / event model.

Every event from Database, Server, and Security sources is stored here.
The WebSocket broadcaster reads from this table and pushes to connected clients.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # One of: "database" | "server" | "security" | "system"
    source: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Fine-grained type: "slow_query", "cpu_high", "login_failed", etc.
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    # "info" | "warning" | "critical"
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    # Arbitrary JSON payload (query, metric value, IP, etc.)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    # Optional: which user triggered the event
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # "new" | "acknowledged" | "resolved"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
    # ISO timestamp of when the event actually occurred (may differ from created_at)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    # Who acknowledged/resolved and when
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_notif_source_sev_status", "source", "severity", "status"),
        Index("ix_notif_created_at", "created_at"),
    )
