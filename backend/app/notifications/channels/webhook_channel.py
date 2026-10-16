"""Generic outbound REST webhook notification channel, for integrating
with any system not covered by the named channels (PagerDuty, Opsgenie,
a custom internal tool, etc.)."""
import httpx

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def send_webhook_alert(payload: dict) -> bool:
    settings = get_settings()
    if not settings.generic_webhook_enabled or not settings.generic_webhook_url:
        return False

    try:
        response = httpx.post(settings.generic_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send webhook alert: %s", exc)
        return False
