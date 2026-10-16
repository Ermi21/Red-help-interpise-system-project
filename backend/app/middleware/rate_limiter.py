"""API rate limiting via slowapi (token-bucket, in-memory by default).

For multi-instance deployments, point slowapi at Redis instead of the
default in-memory backend by passing `storage_uri="redis://..."` to
Limiter — left as in-memory here to keep the base stack dependency-light;
see slowapi's docs for the Redis storage backend.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config.settings import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)
