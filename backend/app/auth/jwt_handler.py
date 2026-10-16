"""JWT access token issuance and verification."""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import PyJWTError

from app.config.settings import get_settings
from app.utils.exceptions import AuthenticationError


def create_access_token(subject: str, role: str, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc
