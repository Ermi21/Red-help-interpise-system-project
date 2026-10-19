"""
Decorators for Redis-based endpoint caching.
"""
from functools import wraps
from typing import Callable

from app.cache.redis_client import cache_get, cache_set
from app.utils.logger import get_logger

logger = get_logger(__name__)


def redis_cached(key_prefix: str, ttl: int):
    """
    Decorator to cache endpoint responses in Redis.
    
    Args:
        key_prefix: Cache key prefix (e.g. "monitoring:database")
        ttl: Time-to-live in seconds
    
    Usage:
        @router.get("/endpoint")
        @redis_cached(key_prefix="monitoring:database", ttl=30)
        def get_data(_: CurrentUser = Depends(get_current_user)):
            return expensive_query()
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key (include user ID if available for per-user caching)
            user = None
            for arg in args:
                if hasattr(arg, 'id') and hasattr(arg, 'username'):
                    user = arg
                    break
            if not user:
                user = kwargs.get('_')
            
            # Use generic cache key (same for all users) for monitoring endpoints
            cache_key = f"{key_prefix}:shared"
            
            # Try cache first
            try:
                cached = cache_get(cache_key)
                if cached is not None:
                    logger.debug(f"Redis cache HIT: {cache_key}")
                    return cached
            except Exception as e:
                logger.debug(f"Redis cache_get error (proceeding without cache): {e}")
            
            # Cache miss or Redis unavailable - execute function
            logger.debug(f"Redis cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache the result (non-blocking, failures are logged but don't break the endpoint)
            try:
                cache_set(cache_key, result, ttl)
            except Exception as e:
                logger.debug(f"Redis cache_set error (result still returned): {e}")
            
            return result
        
        return wrapper
    return decorator
