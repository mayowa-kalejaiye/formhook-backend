"""
Simple in-memory caching service for frequently accessed data.
For production, consider using Redis or Memcached for distributed caching.
"""
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
import threading
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with expiration."""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at


class CacheService:
    """
    Simple in-memory cache with TTL support.
    Thread-safe for concurrent access.
    """
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        Returns None if key doesn't exist or has expired.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                logger.debug(f"Cache expired: {key}")
                return None
            
            logger.debug(f"Cache hit: {key}")
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """
        Set value in cache with TTL (default 5 minutes).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (default 300 = 5 minutes)
        """
        with self._lock:
            self._cache[key] = CacheEntry(value, ttl_seconds)
            logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
    
    def delete(self, key: str):
        """Delete a specific key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted: {key}")
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")
    
    def cleanup_expired(self):
        """Remove all expired entries from cache."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cache cleanup: {len(expired_keys)} expired entries removed")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for entry in self._cache.values() if entry.is_expired())
            active = total - expired
            
            return {
                "total_entries": total,
                "active_entries": active,
                "expired_entries": expired
            }
    
    def get_or_set(self, key: str, factory: Callable[[], Any], ttl_seconds: int = 300) -> Any:
        """
        Get value from cache, or compute and cache it if not present.
        
        Args:
            key: Cache key
            factory: Function to call to compute value if not in cache
            ttl_seconds: Time to live in seconds
            
        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value
        
        # Compute value
        value = factory()
        self.set(key, value, ttl_seconds)
        logger.debug(f"Cache computed and set: {key}")
        return value


# Global cache instance
cache = CacheService()


# Decorator for caching function results
def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live in seconds
        key_prefix: Prefix for cache key
    
    Example:
        @cached(ttl_seconds=60, key_prefix="user_forms")
        def get_user_forms(user_id: int):
            return db.query(Form).filter(Form.user_id == user_id).all()
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator
