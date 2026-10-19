"""
Expanded Security Monitoring API.

Endpoints
---------
GET  /security/login-events        — paginated login audit log
GET  /security/audit-trail         — full user action audit log
GET  /security/blocked-queries     — prompt-injection / blocked SQL log
GET  /security/rbac                — current RBAC assignments
GET  /security/users               — user list with last-login info
POST /security/users/{id}/lock     — lock an account (admin)
POST /security/users/{id}/unlock   — unlock an account (admin)
GET  /security/stats               — aggregated security metrics summary
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db_session, require_role
from app.auth.rbac import Role
from app.models.audit_log import AuditLog
from app.models.login_event import LoginEvent
from app.models.notification import Notification
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/security", tags=["Security Detail"])


# ── Login events ───────────────────────────────────────────────────────────────

@router.get("/login-events")
def get_login_events(
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(require_role(Role.ANALYST)),
    success: bool | None = Query(None),
    username: str | None = Query(None),
    ip_address: str | None = Query(None),
    hours: int = Query(24, ge=1, le=720),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(LoginEvent)
        .where(LoginEvent.created_at > cutoff)
        .order_by(LoginEvent.created_at.desc())
    )
    if success is not None:
        stmt = stmt.where(LoginEvent.success == success)
    if username:
        stmt = stmt.where(LoginEvent.username.ilike(f"%{username}%"))
    if ip_address:
        stmt = stmt.where(LoginEvent.ip_address == ip_address)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    offset = (page - 1) * page_size
    items = db.execute(stmt.offset(offset).limit(page_size)).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": e.id,
                "username": e.username,
                "success": e.success,
                "ip_address": e.ip_address,
                "device_type": e.device_type,
                "country": e.country,
                "city": e.city,
                "failure_reason": e.failure_reason,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in items
        ],
    }


# ── Audit trail ────────────────────────────────────────────────────────────────

@router.get("/audit-trail")
def get_audit_trail(
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(require_role(Role.ANALYST)),
    action: str | None = Query(None),
    username: str | None = Query(None),
    outcome: str | None = Query(None),
    search: str | None = Query(None),
    hours: int = Query(24, ge=1, le=720),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(AuditLog)
        .where(AuditLog.created_at > cutoff)
        .order_by(AuditLog.created_at.desc())
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if username:
        stmt = stmt.where(AuditLog.username.ilike(f"%{username}%"))
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            AuditLog.description.ilike(like) | AuditLog.action.ilike(like)
        )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    offset = (page - 1) * page_size
    items = db.execute(stmt.offset(offset).limit(page_size)).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": a.id,
                "username": a.username,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "description": a.description,
                "outcome": a.outcome,
                "ip_address": a.ip_address,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ],
    }


# ── Blocked queries ────────────────────────────────────────────────────────────

@router.get("/blocked-queries")
def get_blocked_queries(
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(require_role(Role.ANALYST)),
    hours: int = Query(24, ge=1, le=720),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Return prompt-injection and blocked-SQL events from the notifications table."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(Notification)
        .where(
            Notification.event_type.in_(["prompt_injection", "sql_blocked", "readonly_violation"]),
            Notification.created_at > cutoff,
        )
        .order_by(Notification.created_at.desc())
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    offset = (page - 1) * page_size
    items = db.execute(stmt.offset(offset).limit(page_size)).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": n.id,
                "event_type": n.event_type,
                "severity": n.severity,
                "title": n.title,
                "message": n.message,
                "metadata": n.metadata_json,
                "user_id": n.user_id,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


# ── RBAC & user list ───────────────────────────────────────────────────────────

@router.get("/rbac")
def get_rbac(
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(require_role(Role.ADMIN)),
):
    """Return all users with their current role assignment."""
    users = db.execute(select(User).order_by(User.username)).scalars().all()
    return {
        "roles": ["viewer", "analyst", "admin"],
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


# ── Lock / unlock account ──────────────────────────────────────────────────────

@router.post("/users/{user_id}/lock")
def lock_user(
    user_id: str,
    db: Session = Depends(get_db_session),
    current: CurrentUser = Depends(require_role(Role.ADMIN)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="Cannot lock your own account")
    user.is_active = False
    db.commit()

    # Emit a security event
    from app.core.event_bus import publish_event_sync
    publish_event_sync(
        source="security",
        event_type="account_locked",
        severity="warning",
        title=f"Account locked: {user.username}",
        message=f"Admin {current.username} locked account {user.username}.",
        metadata={"locked_user_id": user_id, "locked_by": current.username},
        user_id=current.id,
    )
    return {"ok": True, "username": user.username, "is_active": False}


@router.post("/users/{user_id}/unlock")
def unlock_user(
    user_id: str,
    db: Session = Depends(get_db_session),
    current: CurrentUser = Depends(require_role(Role.ADMIN)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    return {"ok": True, "username": user.username, "is_active": True}


# ── Security stats summary ─────────────────────────────────────────────────────

@router.get("/stats")
def get_security_stats(
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(require_role(Role.ANALYST)),
    hours: int = Query(24, ge=1, le=720),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Login stats
    from sqlalchemy import case
    login_stats = db.execute(
        select(
            func.count().label("total"),
            func.sum(
                case((LoginEvent.success == True, 1), else_=0)
            ).label("success_count"),
        ).where(LoginEvent.created_at > cutoff)
    ).mappings().first()

    fail_total = int((login_stats["total"] or 0)) - int((login_stats["success_count"] or 0))

    # Unique IPs
    unique_ips = db.execute(
        select(func.count(func.distinct(LoginEvent.ip_address)))
        .where(LoginEvent.created_at > cutoff)
    ).scalar_one()

    # Active users
    active_users = db.execute(
        select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
    ).scalar_one()

    # Security events
    sec_notifs = db.execute(
        select(
            Notification.severity,
            func.count().label("cnt"),
        )
        .where(
            Notification.source == "security",
            Notification.created_at > cutoff,
        )
        .group_by(Notification.severity)
    ).mappings().all()

    sev_counts: dict = {"critical": 0, "warning": 0, "info": 0}
    for r in sec_notifs:
        sev_counts[r["severity"]] = int(r["cnt"])

    return {
        "window_hours": hours,
        "login_attempts": int(login_stats["total"] or 0),
        "login_failures": fail_total,
        "unique_ips": unique_ips,
        "active_users": active_users,
        "security_events": sev_counts,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
