"""
Cache Service Tests
===================

Tests for the in-memory caching service.
"""

import time
import threading
import pytest

from app.services.cache_service import CacheService, CachedItem, CacheKeys


class TestCachedItem:
    """Tests for CachedItem dataclass."""
    
    def test_is_not_expired_when_fresh(self):
        """Fresh item should not be expired."""
        item = CachedItem(data="test", ttl_seconds=60)
        assert item.is_expired is False
    
    def test_is_expired_after_ttl(self):
        """Item should be expired after TTL."""
        item = CachedItem(data="test", ttl_seconds=0)
        # Give a tiny bit of time to pass
        time.sleep(0.01)
        assert item.is_expired is True
    
    def test_age_seconds(self):
        """Should correctly calculate age."""
        item = CachedItem(data="test", ttl_seconds=60)
        time.sleep(0.1)
        assert item.age_seconds >= 0.1


class TestCacheService:
    """Tests for CacheService."""
    
    @pytest.fixture
    def cache(self) -> CacheService:
        """Create a fresh cache service for each test."""
        # Create a new instance by resetting the singleton
        CacheService._instance = None
        service = CacheService()
        yield service
        # Cleanup
        service.clear()
        CacheService._instance = None
    
    def test_set_and_get(self, cache: CacheService):
        """Should store and retrieve values."""
        cache.set("key1", "value1")
        
        item = cache.get("key1")
        assert item is not None
        assert item.data == "value1"
    
    def test_get_data(self, cache: CacheService):
        """Should retrieve just the data."""
        cache.set("key1", "value1")
        
        data = cache.get_data("key1")
        assert data == "value1"
    
    def test_get_nonexistent_key(self, cache: CacheService):
        """Should return None for nonexistent key."""
        assert cache.get("nonexistent") is None
        assert cache.get_data("nonexistent") is None
    
    def test_delete(self, cache: CacheService):
        """Should delete items."""
        cache.set("key1", "value1")
        
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
    
    def test_delete_nonexistent(self, cache: CacheService):
        """Should return False when deleting nonexistent key."""
        assert cache.delete("nonexistent") is False
    
    def test_clear(self, cache: CacheService):
        """Should clear all items."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        count = cache.clear()
        
        assert count == 2
        assert cache.size() == 0
    
    def test_has(self, cache: CacheService):
        """Should check if key exists."""
        cache.set("key1", "value1")
        
        assert cache.has("key1") is True
        assert cache.has("nonexistent") is False
    
    def test_size(self, cache: CacheService):
        """Should return correct size."""
        assert cache.size() == 0
        
        cache.set("key1", "value1")
        assert cache.size() == 1
        
        cache.set("key2", "value2")
        assert cache.size() == 2
    
    def test_custom_ttl(self, cache: CacheService):
        """Should respect custom TTL."""
        cache.set("key1", "value1", ttl_seconds=0)
        
        # Give a tiny bit of time to pass
        time.sleep(0.01)
        
        # Item should be expired
        assert cache.get("key1") is None
    
    def test_expired_items_removed_on_get(self, cache: CacheService):
        """Expired items should be removed when accessed."""
        cache.set("key1", "value1", ttl_seconds=0)
        
        time.sleep(0.01)
        
        # Access should remove the expired item
        cache.get("key1")
        
        # Size might still include it until cleanup, but get returns None
        assert cache.get("key1") is None
    
    def test_thread_safety(self, cache: CacheService):
        """Should be thread-safe."""
        errors = []
        
        def writer():
            try:
                for i in range(100):
                    cache.set(f"key_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for i in range(100):
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestCacheKeys:
    """Tests for CacheKeys constants."""
    
    def test_trending_livestreams_key(self):
        """Should have correct key for trending livestreams."""
        assert CacheKeys.TRENDING_LIVESTREAMS == "trending_livestreams"
    
    def test_livestream_key(self):
        """Should generate correct key for livestream."""
        assert CacheKeys.livestream(123) == "livestream:123"
    
    def test_viewership_history_key(self):
        """Should generate correct key for viewership history."""
        assert CacheKeys.viewership_history(456) == "viewership:456"
