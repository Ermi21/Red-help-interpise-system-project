"""
Login audit log — every login attempt (success or failure) is recorded here.
Used by the Security Monitoring dashboard for brute-force detection and
impossible-travel analysis.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LoginEvent(Base):
    __tablename__ = "login_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)   # IPv6 max 45
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Derived from user_agent / heuristic
    device_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # desktop/mobile/bot
    # Country/city resolved from IP (best-effort, may be None)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Why the login failed (generic — never "user not found" vs "wrong password")
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_loginevent_username_created", "username", "created_at"),
        Index("ix_loginevent_ip_created", "ip_address", "created_at"),
    )
