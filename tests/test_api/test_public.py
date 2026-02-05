"""
Public API Tests
================

Tests for unauthenticated public endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models import Livestream


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, async_client: AsyncClient):
        """Health check should return 200 OK."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_check_response_structure(self, async_client: AsyncClient):
        """Health check should return expected structure."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "database" in data
    
    @pytest.mark.asyncio
    async def test_health_check_shows_healthy(self, async_client: AsyncClient):
        """Health check should show healthy status."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        
        assert data["status"] == "healthy"


class TestTrendingLivestreamsEndpoint:
    """Tests for /livestreams endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_trending_returns_200(self, async_client: AsyncClient):
        """Trending endpoint should return 200 OK."""
        response = await async_client.get("/api/v1/livestreams")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_trending_default_count(self, async_client: AsyncClient):
        """Should return default count when not specified."""
        response = await async_client.get("/api/v1/livestreams")
        data = response.json()
        
        assert "items" in data
        assert "count" in data
        assert isinstance(data["items"], list)
    
    @pytest.mark.asyncio
    async def test_get_trending_with_count_param(self, async_client: AsyncClient):
        """Should respect count parameter."""
        response = await async_client.get("/api/v1/livestreams?count=5")
        assert response.status_code == 200
        data = response.json()
        
        # Count should be <= requested
        assert data["count"] <= 5
    
    @pytest.mark.asyncio
    async def test_get_trending_count_validation_min(self, async_client: AsyncClient):
        """Should reject count < 1."""
        response = await async_client.get("/api/v1/livestreams?count=0")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_trending_count_validation_max(self, async_client: AsyncClient):
        """Should reject count > 100."""
        response = await async_client.get("/api/v1/livestreams?count=101")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_trending_with_data(
        self,
        async_client: AsyncClient,
        sample_livestream: Livestream,
        sample_viewership,
    ):
        """Should return livestreams with viewership data."""
        response = await async_client.get("/api/v1/livestreams")
        data = response.json()
        
        # Should have items if data exists
        assert "items" in data
        
        # If we have items, check structure
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "youtube_video_id" in item
            assert "name" in item
            assert "channel" in item
            assert "current_viewers" in item
            assert "rank" in item


class TestRootEndpoint:
    """Tests for root / endpoint."""
    
    @pytest.mark.asyncio
    async def test_root_returns_200(self, async_client: AsyncClient):
        """Root endpoint should return 200 OK."""
        response = await async_client.get("/")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_root_contains_api_info(self, async_client: AsyncClient):
        """Root should contain API information."""
        response = await async_client.get("/")
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "docs" in data
