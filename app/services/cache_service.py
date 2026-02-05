"""
Cache Service
=============

Thread-safe in-memory caching with TTL support.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar

from app.config import get_settings


T = TypeVar("T")


@dataclass
class CachedItem(Generic[T]):
    """
    A cached item with metadata.
    
    Attributes:
        data: The cached data
        cached_at: When the data was cached
        ttl_seconds: Time-to-live in seconds
    """
    data: T
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 300
    
    @property
    def is_expired(self) -> bool:
        """Check if the cached item has expired."""
        now = datetime.now(timezone.utc)
        age = (now - self.cached_at).total_seconds()
        return age >= self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get the age of the cached item in seconds."""
        now = datetime.now(timezone.utc)
        return (now - self.cached_at).total_seconds()


class CacheService:
    """
    Thread-safe in-memory cache service.
    
    Provides a simple key-value cache with TTL support.
    Uses threading locks for thread safety.
    
    Features:
        - Configurable TTL per cache or per item
        - Thread-safe operations
        - Automatic expiration checks
        - Max items limit
    """
    
    _instance: Optional["CacheService"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "CacheService":
        """Singleton pattern - ensure only one CacheService exists."""
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
            return cls._instance
    
    def __init__(self) -> None:
        """Initialize the cache service."""
        if getattr(self, "_initialized", False):
            return
        
        settings = get_settings()
        self._cache: dict[str, CachedItem] = {}
        self._cache_lock = threading.RLock()
        self._default_ttl = settings.cache_ttl_seconds
        self._max_items = settings.cache_max_items
        self._initialized = True
    
    def get(self, key: str) -> Optional[CachedItem]:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key
        
        Returns:
            CachedItem if found and not expired, None otherwise
        """
        with self._cache_lock:
            item = self._cache.get(key)
            
            if item is None:
                return None
            
            if item.is_expired:
                del self._cache[key]
                return None
            
            return item
    
    def get_data(self, key: str) -> Optional[T]:
        """
        Get just the data from a cached item.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data if found and not expired, None otherwise
        """
        item = self.get(key)
        return item.data if item else None
    
    def set(
        self, 
        key: str, 
        data: T, 
        ttl_seconds: Optional[int] = None,
    ) -> CachedItem[T]:
        """
        Store an item in the cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_seconds: TTL in seconds (defaults to service default)
        
        Returns:
            The created CachedItem
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        item = CachedItem(data=data, ttl_seconds=ttl)
        
        with self._cache_lock:
            # Evict expired items if we're at max capacity
            if len(self._cache) >= self._max_items and key not in self._cache:
                self._evict_expired()
            
            # If still at max capacity, evict oldest item
            if len(self._cache) >= self._max_items and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = item
        
        return item
    
    def delete(self, key: str) -> bool:
        """
        Delete an item from the cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if item was deleted, False if not found
        """
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> int:
        """
        Clear all items from the cache.
        
        Returns:
            Number of items cleared
        """
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def has(self, key: str) -> bool:
        """
        Check if a non-expired item exists in the cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if item exists and is not expired
        """
        return self.get(key) is not None
    
    def size(self) -> int:
        """
        Get the current cache size.
        
        Returns:
            Number of items in cache (including expired)
        """
        with self._cache_lock:
            return len(self._cache)
    
    def _evict_expired(self) -> int:
        """
        Remove all expired items from the cache.
        
        Returns:
            Number of items evicted
        
        Note: Must be called with lock held.
        """
        expired_keys = [
            key for key, item in self._cache.items() 
            if item.is_expired
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
    
    def _evict_oldest(self) -> bool:
        """
        Remove the oldest item from the cache.
        
        Returns:
            True if an item was evicted
        
        Note: Must be called with lock held.
        """
        if not self._cache:
            return False
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].cached_at
        )
        del self._cache[oldest_key]
        return True


# Global instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Get the global CacheService instance.
    
    Returns:
        CacheService singleton instance
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# Cache keys constants
class CacheKeys:
    """Cache key constants for type safety."""
    
    TRENDING_LIVESTREAMS = "trending_livestreams"
    
    @staticmethod
    def livestream(livestream_id: int) -> str:
        """Get cache key for a specific livestream."""
        return f"livestream:{livestream_id}"
    
    @staticmethod
    def viewership_history(livestream_id: int) -> str:
        """Get cache key for livestream viewership history."""
        return f"viewership:{livestream_id}"
