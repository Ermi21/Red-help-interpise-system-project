"""Telegram notification channel via the Bot API.

Note: this is a distinct integration from the team's Telegram BOT
frontend — this channel only ever sends outbound admin alert messages
via the Bot API's sendMessage call, it does not implement bot commands
or receive user messages."""
import httpx

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def send_telegram_alert(text: str) -> bool:
    settings = get_settings()
    if not settings.telegram_enabled or not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        response = httpx.post(url, json={"chat_id": settings.telegram_chat_id, "text": text}, timeout=10)
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send Telegram alert: %s", exc)
        return False
