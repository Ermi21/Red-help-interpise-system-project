"""
Notification orchestrator.

Takes a structured alert and fans it out to every enabled channel. The
backend ONLY sends notifications — it never takes any corrective action
against the target database itself.
"""
from datetime import datetime, timezone

from app.config.settings import get_settings
from app.notifications.channels.email_channel import send_email_alert
from app.notifications.channels.slack_channel import send_slack_alert
from app.notifications.channels.teams_channel import send_teams_alert
from app.notifications.channels.telegram_channel import send_telegram_alert
from app.notifications.channels.webhook_channel import send_webhook_alert
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _meets_threshold(severity: str, minimum: str) -> bool:
    return _SEVERITY_RANK.get(severity, 0) >= _SEVERITY_RANK.get(minimum, 2)


def _format_message(title: str, severity: str, description: str, recommendation: str) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    return (
        f"[{severity.upper()}] {title}\n"
        f"Time: {timestamp}\n\n"
        f"Details: {description}\n\n"
        f"Recommended action: {recommendation}\n\n"
        f"(This is a notification only — no automated action has been taken "
        f"against the database.)"
    )


def dispatch_alert(title: str, severity: str, description: str, recommendation: str, category: str = "health") -> dict:
    """Send an alert to every enabled channel whose severity threshold is met.

    Returns a dict of {channel_name: bool} indicating delivery success,
    which callers persist alongside the Alert record for auditability.
    """
    settings = get_settings()
    results: dict[str, bool] = {}

    if not _meets_threshold(severity, settings.notify_min_severity):
        logger.info("Alert '%s' below notification threshold (%s < %s); not dispatched.", title, severity, settings.notify_min_severity)
        return results

    message = _format_message(title, severity, description, recommendation)

    if settings.email_enabled:
        results["email"] = send_email_alert(subject=f"[{severity.upper()}] {title}", body=message)
    if settings.telegram_enabled:
        results["telegram"] = send_telegram_alert(message)
    if settings.slack_enabled:
        results["slack"] = send_slack_alert(message)
    if settings.teams_enabled:
        results["teams"] = send_teams_alert(title=title, text=message)
    if settings.generic_webhook_enabled:
        results["webhook"] = send_webhook_alert(
            {
                "title": title,
                "severity": severity,
                "category": category,
                "description": description,
                "recommendation": recommendation,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    logger.info("Dispatched alert '%s' (severity=%s) to channels: %s", title, severity, results)
    return results
