"""Email notification channel via SMTP."""
import smtplib
from email.mime.text import MIMEText

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def send_email_alert(subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.email_enabled or not settings.smtp_host or not settings.alert_email_to:
        return False

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.alert_email_from
    message["To"] = ", ".join(settings.alert_email_to)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.alert_email_from, settings.alert_email_to, message.as_string())
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send email alert: %s", exc)
        return False
