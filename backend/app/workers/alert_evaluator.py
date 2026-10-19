"""
Alert rule evaluator — runs every 30 seconds.

Checks the `login_events` table for brute-force patterns and the
`notifications` table for unacknowledged critical events that need
escalation.  Fires new events via the event bus when rules trigger.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from app.core.event_bus import publish_event
from app.utils.logger import get_logger

logger = get_logger(__name__)

# How many failed logins within the window counts as a brute-force attack
_BRUTE_FORCE_THRESHOLD = 5
_BRUTE_FORCE_WINDOW_MINUTES = 10

# After how many minutes a critical unacknowledged alert gets re-notified
_ESCALATION_MINUTES = 15


# Track last alerted brute-force IPs to avoid spamming
_brute_force_alerted: dict[str, datetime] = {}


def _query_brute_force_sync() -> list[dict]:
    from app.database.connection import app_session
    from sqlalchemy import text

    window_start = datetime.now(timezone.utc) - timedelta(minutes=_BRUTE_FORCE_WINDOW_MINUTES)
    sql = """
        SELECT ip_address, COUNT(*) AS cnt
        FROM login_events
        WHERE success = false
          AND created_at > :window_start
          AND ip_address IS NOT NULL
        GROUP BY ip_address
        HAVING COUNT(*) >= :threshold
    """
    with app_session() as session:
        return [
            dict(r)
            for r in session.execute(
                text(sql),
                {"window_start": window_start, "threshold": _BRUTE_FORCE_THRESHOLD},
            ).mappings().all()
        ]


async def _check_brute_force() -> None:
    """Detect IPs with >=N failed logins in the past M minutes."""
    try:
        rows = await asyncio.to_thread(_query_brute_force_sync)
        now = datetime.now(timezone.utc)

        for row in rows:
            ip = row["ip_address"]
            cnt = row["cnt"]
            last_alert = _brute_force_alerted.get(ip)
            if last_alert and (now - last_alert) < timedelta(minutes=_BRUTE_FORCE_WINDOW_MINUTES):
                continue
            _brute_force_alerted[ip] = now

            await publish_event(
                source="security",
                event_type="brute_force",
                severity="critical",
                title=f"Brute-force attack detected from {ip}",
                message=(
                    f"{cnt} failed login attempts from IP {ip} "
                    f"in the past {_BRUTE_FORCE_WINDOW_MINUTES} minutes."
                ),
                metadata={"ip_address": ip, "attempt_count": cnt,
                          "window_minutes": _BRUTE_FORCE_WINDOW_MINUTES},
            )
    except Exception as exc:
        logger.warning("Brute-force check failed: %s", exc)


def _fetch_and_escalate_sync() -> list[dict]:
    from app.database.connection import app_session
    from sqlalchemy import text

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_ESCALATION_MINUTES)
    # Strictly exclude already-escalated events and limit to 10
    sql = """
        SELECT id, title, source, event_type
        FROM notifications
        WHERE severity = 'critical'
          AND status = 'new'
          AND event_type != 'escalation'
          AND created_at < :cutoff
        LIMIT 10
    """
    to_escalate = []
    with app_session() as session:
        rows = session.execute(text(sql), {"cutoff": cutoff}).mappings().all()
        for row in rows:
            to_escalate.append(dict(row))
            # Mark original as escalated so it never cascades into an infinite loop
            session.execute(
                text("UPDATE notifications SET status = 'escalated' WHERE id = :id"),
                {"id": row["id"]},
            )
        session.commit()
    return to_escalate


async def _check_escalations() -> None:
    """Re-fire critical notifications older than _ESCALATION_MINUTES (at most once)."""
    try:
        items = await asyncio.to_thread(_fetch_and_escalate_sync)
        for item in items:
            await publish_event(
                source=item["source"],
                event_type="escalation",
                severity="critical",
                title=f"[ESCALATED] {item['title']}",
                message=(
                    f"This critical alert has been unacknowledged for "
                    f"more than {_ESCALATION_MINUTES} minutes."
                ),
                metadata={
                    "original_notification_id": item["id"],
                    "original_event_type": item["event_type"],
                },
            )
    except Exception as exc:
        logger.warning("Escalation check failed: %s", exc)


def _cleanup_old_notifications_sync() -> None:
    from app.database.connection import app_session
    from sqlalchemy import text

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    with app_session() as session:
        deleted = session.execute(
            text("DELETE FROM notifications WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        ).rowcount
        if deleted:
            logger.info("Retention: deleted %d old notifications", deleted)


async def _cleanup_old_notifications() -> None:
    """Delete notifications older than 90 days to enforce retention policy."""
    try:
        await asyncio.to_thread(_cleanup_old_notifications_sync)
    except Exception as exc:
        logger.warning("Retention cleanup failed: %s", exc)


async def run_alert_evaluator(interval_s: int = 30) -> None:
    """Main loop — run as asyncio.create_task() from FastAPI lifespan."""
    logger.info("Alert evaluator started (interval=%ds)", interval_s)
    await asyncio.sleep(5)  # Yield to event loop to allow Uvicorn port binding first
    iteration = 0
    while True:
        await _check_brute_force()
        await _check_escalations()
        # Run retention cleanup once per hour (every 120 iterations × 30 s = 3600 s)
        if iteration % 120 == 0:
            await _cleanup_old_notifications()
        iteration += 1
        await asyncio.sleep(interval_s)

