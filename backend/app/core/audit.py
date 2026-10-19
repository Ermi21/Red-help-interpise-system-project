"""
Audit log helper — thin wrapper so any endpoint can record user actions
with one call without importing the ORM model directly.

Usage
-----
from app.core.audit import record_audit

record_audit(
    user_id=current.id,
    username=current.username,
    action="schema_refresh",
    description="User triggered a full schema refresh",
    ip_address=request.client.host,
    outcome="success",
    context={"tables_refreshed": 12},
)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


def record_audit(
    action: str,
    description: str = "",
    user_id: str | None = None,
    username: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    outcome: str = "success",
    context: dict[str, Any] | None = None,
) -> None:
    """
    Persist an audit log entry synchronously.
    Never raises — audit logging must never break the calling request.
    """
    try:
        from app.database.connection import app_session
        from app.models.audit_log import AuditLog

        with app_session() as session:
            session.add(AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description[:1000] if description else "",
                context_json=context or {},
                ip_address=ip_address,
                outcome=outcome,
                created_at=datetime.now(timezone.utc),
            ))
    except Exception as exc:
        logger.warning("Audit log write failed: %s", exc)
