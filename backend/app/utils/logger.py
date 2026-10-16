"""
Structured logging configuration.

Every log line is emitted as JSON so it can be shipped to and indexed by
log aggregation tools (ELK, Loki, CloudWatch, etc.) in production.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from pythonjsonlogger import jsonlogger

from app.config.settings import get_settings

_CONFIGURED = False


def _build_formatter() -> jsonlogger.JsonFormatter:
    return jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )


def configure_logging() -> None:
    """Idempotently configure root logging handlers (console + rotating file)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    os.makedirs(settings.log_dir, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_build_formatter())
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        os.path.join(settings.log_dir, "backend.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(_build_formatter())
    root.addHandler(file_handler)

    # Quiet down noisy third-party loggers unless we're debugging.
    if not settings.debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("chromadb").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
