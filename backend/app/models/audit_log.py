"""
Full audit trail for every meaningful user action (search, export, permission
change, schema refresh, etc.).  Used by the Security Monitoring dashboard.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Who did it
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # What they did: "chat_query", "schema_refresh", "export", "permission_change", etc.
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    # Which resource was affected
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Short human-readable summary
    description: Mapped[str] = mapped_column(Text, default="")
    # Full context (request body snippet, old/new values, etc.) — never raw passwords
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # "success" | "failure" | "blocked"
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_auditlog_user_created", "user_id", "created_at"),
        Index("ix_auditlog_action_created", "action", "created_at"),
    )
