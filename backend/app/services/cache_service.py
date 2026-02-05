"""Thread-safe caching service for ranked livestreams."""
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.livestream import LivestreamRanked


@dataclass
class CacheEntry:
    """A single cache entry with TTL."""
    
    data: List[LivestreamRanked]
    created_at: datetime
    ttl_seconds: int
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        now = datetime.now(timezone.utc)
        age = (now - self.created_at).total_seconds()
        return age >= self.ttl_seconds
    
    @property
    def remaining_ttl(self) -> int:
        """Get remaining TTL in seconds."""
        now = datetime.now(timezone.utc)
        age = (now - self.created_at).total_seconds()
        return max(0, int(self.ttl_seconds - age))


class RankingCache:
    """Thread-safe in-memory cache for ranked livestreams.
    
    This cache stores the top N ranked livestreams and serves
    requests from cache when valid, avoiding repeated computation.
    """
    
    def __init__(self, ttl_seconds: int = 300, max_items: int = 100):
        """Initialize the cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries (default: 5 minutes)
            max_items: Maximum items to store in cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._cache: Optional[CacheEntry] = None
        self._lock = threading.RLock()
    
    def get(self, count: int = 10) -> Optional[tuple[List[LivestreamRanked], datetime, int]]:
        """Get cached rankings if valid.
        
        Args:
            count: Number of items to return
            
        Returns:
            Tuple of (items, cached_at, remaining_ttl) if cache hit, None otherwise
        """
        with self._lock:
            if self._cache is None or self._cache.is_expired:
                return None
            
            items = self._cache.data[:count]
            return items, self._cache.created_at, self._cache.remaining_ttl
    
    def set(self, data: List[LivestreamRanked]) -> None:
        """Update the cache with new data.
        
        Args:
            data: List of ranked livestreams (should be pre-sorted)
        """
        with self._lock:
            # Limit to max items
            limited_data = data[:self.max_items]
            
            self._cache = CacheEntry(
                data=limited_data,
                created_at=datetime.now(timezone.utc),
                ttl_seconds=self.ttl_seconds,
            )
    
    def invalidate(self) -> None:
        """Invalidate the cache."""
        with self._lock:
            self._cache = None
    
    @property
    def is_valid(self) -> bool:
        """Check if cache has valid data."""
        with self._lock:
            return self._cache is not None and not self._cache.is_expired
    
    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            if self._cache is None:
                return {
                    "has_data": False,
                    "item_count": 0,
                    "is_expired": True,
                    "remaining_ttl": 0,
                }
            
            return {
                "has_data": True,
                "item_count": len(self._cache.data),
                "is_expired": self._cache.is_expired,
                "remaining_ttl": self._cache.remaining_ttl,
                "created_at": self._cache.created_at.isoformat(),
            }


class CacheService:
    """Singleton cache service for the application."""
    
    _instance: Optional["CacheService"] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, ttl_seconds: int = 300, max_items: int = 100):
        if self._initialized:
            return
        
        self.rankings = RankingCache(ttl_seconds=ttl_seconds, max_items=max_items)
        self._initialized = True
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        with cls._lock:
            cls._instance = None
