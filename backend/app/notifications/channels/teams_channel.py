"""Microsoft Teams notification channel via Incoming Webhook."""
import httpx

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def send_teams_alert(title: str, text: str) -> bool:
    settings = get_settings()
    if not settings.teams_enabled or not settings.teams_webhook_url:
        return False

    payload = {"title": title, "text": text}
    try:
        response = httpx.post(settings.teams_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send Teams alert: %s", exc)
        return False
