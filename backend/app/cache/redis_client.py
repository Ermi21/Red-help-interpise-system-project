"""
Redis client for distributed caching across backend instances.
Replaces in-process TTL caches with a shared Redis store.
"""
import json
from typing import Any

from redis import Redis, ConnectionPool
from redis.exceptions import RedisError

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None
_pool: ConnectionPool | None = None


def get_redis() -> Redis:
    """Get or create Redis connection (singleton pattern)."""
    global _redis, _pool
    
    settings = get_settings()
    
    if not settings.redis_enabled:
        raise RuntimeError("Redis is disabled in configuration")
    
    if _redis is None:
        try:
            _pool = ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                max_connections=50,
            )
            _redis = Redis(connection_pool=_pool)
            
            # Test connection
            _redis.ping()
            logger.info(f"Redis connected: {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    return _redis


def cache_get(key: str) -> Any | None:
    """
    Get cached value from Redis.
    Returns None if key doesn't exist or Redis is unavailable.
    """
    try:
        redis = get_redis()
        value = redis.get(key)
        if value is None:
            return None
        return json.loads(value)
    except RedisError as e:
        logger.warning(f"Redis cache_get failed for key '{key}': {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Redis cache value corrupted for key '{key}': {e}")
        return None
    except Exception as e:
        logger.debug(f"Redis unavailable during cache_get: {e}")
        return None


def cache_set(key: str, value: Any, ttl_seconds: int) -> bool:
    """
    Cache value in Redis with TTL.
    Returns True on success, False on failure.
    """
    try:
        redis = get_redis()
        serialized = json.dumps(value)
        redis.setex(key, ttl_seconds, serialized)
        logger.debug(f"Redis cached: {key} (TTL={ttl_seconds}s)")
        return True
    except RedisError as e:
        logger.warning(f"Redis cache_set failed for key '{key}': {e}")
        return False
    except Exception as e:
        logger.debug(f"Redis unavailable during cache_set: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Delete a single cache key."""
    try:
        redis = get_redis()
        deleted = redis.delete(key)
        logger.debug(f"Redis deleted key: {key} (existed={bool(deleted)})")
        return bool(deleted)
    except Exception as e:
        logger.warning(f"Redis cache_delete failed for key '{key}': {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching pattern (e.g. 'monitoring:*').
    Returns number of keys deleted.
    """
    try:
        redis = get_redis()
        keys = redis.keys(pattern)
        if keys:
            count = redis.delete(*keys)
            logger.info(f"Redis invalidated {count} keys matching pattern: {pattern}")
            return count
        return 0
    except Exception as e:
        logger.warning(f"Redis cache invalidation failed for pattern '{pattern}': {e}")
        return 0


def get_cache_stats() -> dict:
    """Get Redis cache statistics for monitoring."""
    try:
        redis = get_redis()
        info = redis.info("stats")
        memory = redis.info("memory")
        
        total_keys = redis.dbsize()
        
        # Calculate hit rate
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total_ops = hits + misses
        hit_rate = (hits / total_ops * 100) if total_ops > 0 else 0
        
        return {
            "status": "connected",
            "total_keys": total_keys,
            "hit_rate_percent": round(hit_rate, 2),
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "memory_used_mb": round(memory.get("used_memory", 0) / 1_048_576, 2),
            "memory_peak_mb": round(memory.get("used_memory_peak", 0) / 1_048_576, 2),
            "evicted_keys": info.get("evicted_keys", 0),
            "expired_keys": info.get("expired_keys", 0),
        }
    except Exception as e:
        logger.warning(f"Failed to get Redis stats: {e}")
        return {
            "status": "unavailable",
            "error": str(e)
        }


def invalidate_all_monitoring_caches() -> None:
    """Force-expire every monitoring cache (called after DB connection change)."""
    patterns = [
        "monitoring:*",
        "schema:*",
        "rag:*",
    ]
    for pattern in patterns:
        cache_delete_pattern(pattern)
    logger.info("All monitoring caches invalidated via Redis")
