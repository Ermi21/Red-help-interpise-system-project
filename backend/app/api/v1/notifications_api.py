"""
Notifications REST API + SSE fallback stream.

Endpoints
---------
GET  /notifications          — paginated list with filters
GET  /notifications/stream   — Server-Sent Events fallback (no WebSocket)
GET  /notifications/summary  — unread counts by source/severity
POST /notifications/{id}/acknowledge
POST /notifications/{id}/resolve
POST /notifications/bulk-action
DELETE /notifications/{id}   — admin only
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db_session, require_role
from app.auth.rbac import Role
from app.core.event_bus import subscribe, unsubscribe
from app.models.notification import Notification
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: str
    source: str
    event_type: str
    severity: str
    title: str
    message: str
    metadata_json: dict
    user_id: str | None
    status: str
    occurred_at: datetime
    created_at: datetime
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_note: str | None = None

    model_config = {"from_attributes": True}


class ResolveRequest(BaseModel):
    note: str = ""


class BulkActionRequest(BaseModel):
    ids: list[str]
    action: str  # "acknowledge" | "resolve" | "delete"
    note: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_filters(stmt, source, severity, status, search):
    if source:
        stmt = stmt.where(Notification.source == source)
    if severity:
        stmt = stmt.where(Notification.severity == severity)
    if status:
        stmt = stmt.where(Notification.status == status)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            Notification.title.ilike(like) | Notification.message.ilike(like)
        )
    return stmt


# ── List (paginated) ──────────────────────────────────────────────────────────

@router.get("", response_model=dict)
def list_notifications(
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(get_current_user),
    source:   str | None = Query(None),
    severity: str | None = Query(None),
    status:   str | None = Query(None),
    search:   str | None = Query(None),
    page:     int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    offset = (page - 1) * page_size
    base = select(Notification).order_by(Notification.created_at.desc())
    base = _apply_filters(base, source, severity, status, search)

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    items = db.execute(base.offset(offset).limit(page_size)).scalars().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [NotificationOut.model_validate(n) for n in items],
    }


# ── Summary counts ────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(get_current_user),
):
    rows = db.execute(
        select(
            Notification.source,
            Notification.severity,
            Notification.status,
            func.count().label("cnt"),
        ).group_by(
            Notification.source,
            Notification.severity,
            Notification.status,
        )
    ).mappings().all()

    summary: dict = {
        "total_new": 0,
        "critical_new": 0,
        "warning_new": 0,
        "by_source": {},
    }
    for r in rows:
        src = r["source"]
        sev = r["severity"]
        sts = r["status"]
        cnt = r["cnt"]
        if src not in summary["by_source"]:
            summary["by_source"][src] = {"new": 0, "critical": 0, "warning": 0}
        if sts == "new":
            summary["total_new"] += cnt
            summary["by_source"][src]["new"] += cnt
            if sev == "critical":
                summary["critical_new"] += cnt
                summary["by_source"][src]["critical"] += cnt
            elif sev == "warning":
                summary["warning_new"] += cnt
                summary["by_source"][src]["warning"] += cnt
    return summary


# ── Acknowledge ───────────────────────────────────────────────────────────────

@router.post("/{notification_id}/acknowledge")
def acknowledge(
    notification_id: str,
    db: Session = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
):
    n = db.get(Notification, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.status = "acknowledged"
    db.commit()
    return {"ok": True}


# ── Resolve ───────────────────────────────────────────────────────────────────

@router.post("/{notification_id}/resolve")
def resolve(
    notification_id: str,
    body: ResolveRequest,
    db: Session = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
):
    n = db.get(Notification, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.status = "resolved"
    n.resolved_by = current.username
    n.resolved_at = datetime.now(timezone.utc)
    n.resolution_note = body.note
    db.commit()
    return {"ok": True}


# ── Bulk action ───────────────────────────────────────────────────────────────

@router.post("/bulk-action")
def bulk_action(
    body: BulkActionRequest,
    db: Session = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
):
    if body.action not in ("acknowledge", "resolve", "delete"):
        raise HTTPException(status_code=400, detail="Invalid action")

    if body.action == "delete":
        # Admin only
        from app.api.deps import require_role
        from app.auth.rbac import Role
        if not Role(current.role).rank >= Role.ADMIN.rank:
            raise HTTPException(status_code=403, detail="Admin required")
        for nid in body.ids:
            n = db.get(Notification, nid)
            if n:
                db.delete(n)
    else:
        new_status = "acknowledged" if body.action == "acknowledge" else "resolved"
        for nid in body.ids:
            n = db.get(Notification, nid)
            if n:
                n.status = new_status
                if body.action == "resolve":
                    n.resolved_by = current.username
                    n.resolved_at = datetime.now(timezone.utc)
                    n.resolution_note = body.note

    db.commit()
    return {"ok": True, "affected": len(body.ids)}


# ── Delete (admin) ────────────────────────────────────────────────────────────

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db_session),
    _: CurrentUser = Depends(require_role(Role.ADMIN)),
):
    n = db.get(Notification, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(n)
    db.commit()
    return {"ok": True}


# ── SSE fallback stream ───────────────────────────────────────────────────────

@router.get("/stream")
async def sse_stream(
    token: str = Query(..., description="JWT access token"),
):
    """
    Server-Sent Events fallback for environments where WebSockets are blocked.
    The client connects once and receives events as text/event-stream.
    Auto-reconnect is handled by the browser's EventSource API.
    """
    from app.auth.jwt_handler import decode_access_token
    try:
        payload = decode_access_token(token)
        role = payload.get("role", "viewer")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    async def event_generator():
        queue = await subscribe()
        try:
            # Initial "connected" message
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    continue

                if role == "viewer" and event.get("source") == "security":
                    continue

                yield f"data: {json.dumps({'type': 'event', 'data': event})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
