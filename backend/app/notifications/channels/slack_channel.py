"""Slack notification channel via Incoming Webhook."""
import httpx

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def send_slack_alert(text: str) -> bool:
    settings = get_settings()
    if not settings.slack_enabled or not settings.slack_webhook_url:
        return False

    try:
        response = httpx.post(settings.slack_webhook_url, json={"text": text}, timeout=10)
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send Slack alert: %s", exc)
        return False
