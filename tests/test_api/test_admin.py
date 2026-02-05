"""
Admin API Tests
===============

Tests for JWT-protected admin endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models import Livestream, ViewershipHistory


class TestAdminAuthentication:
    """Tests for admin endpoint authentication."""
    
    @pytest.mark.asyncio
    async def test_admin_endpoints_require_auth(self, async_client: AsyncClient):
        """Admin endpoints should return 401 without token."""
        test_uuid = "00000000-0000-0000-0000-000000000001"
        endpoints = [
            ("GET", "/api/v1/admin/livestreams"),
            ("POST", "/api/v1/admin/livestreams"),
            ("GET", f"/api/v1/admin/livestreams/{test_uuid}"),
            ("PUT", f"/api/v1/admin/livestreams/{test_uuid}"),
            ("DELETE", f"/api/v1/admin/livestreams/{test_uuid}"),
            ("GET", f"/api/v1/admin/livestreams/{test_uuid}/history"),
        ]
        
        for method, url in endpoints:
            if method == "GET":
                response = await async_client.get(url)
            elif method == "POST":
                response = await async_client.post(url, json={})
            elif method == "PUT":
                response = await async_client.put(url, json={})
            elif method == "DELETE":
                response = await async_client.delete(url)
            
            assert response.status_code in [401, 403], f"Expected 401/403 for {method} {url}"
    
    @pytest.mark.asyncio
    async def test_admin_endpoints_reject_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        """Admin endpoints should reject invalid tokens."""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await async_client.get(
            "/api/v1/admin/livestreams",
            headers=headers,
        )
        
        assert response.status_code == 401


class TestListLivestreams:
    """Tests for GET /admin/livestreams endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_livestreams_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return empty list when no livestreams exist."""
        response = await async_client.get(
            "/api/v1/admin/livestreams",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["items"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_livestreams_with_data(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
    ):
        """Should return livestreams when they exist."""
        response = await async_client.get(
            "/api/v1/admin/livestreams",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["id"] == sample_livestream.public_id
    
    @pytest.mark.asyncio
    async def test_list_livestreams_pagination(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
    ):
        """Should support pagination parameters."""
        response = await async_client.get(
            "/api/v1/admin/livestreams?skip=0&limit=10",
            headers=auth_headers,
        )
        
        assert response.status_code == 200


class TestCreateLivestream:
    """Tests for POST /admin/livestreams endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_livestream_with_video_id(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should create livestream with video ID."""
        response = await async_client.post(
            "/api/v1/admin/livestreams",
            headers=auth_headers,
            json={
                "youtube_video_id": "abc12345678",
                "name": "New Livestream",
                "channel": "Test Channel",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["youtube_video_id"] == "abc12345678"
        assert data["name"] == "New Livestream"
        assert data["channel"] == "Test Channel"
        assert "https://www.youtube.com/watch?v=abc12345678" in data["url"]
    
    @pytest.mark.asyncio
    async def test_create_livestream_with_url(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should create livestream from URL."""
        response = await async_client.post(
            "/api/v1/admin/livestreams",
            headers=auth_headers,
            json={
                "youtube_url": "https://www.youtube.com/watch?v=xyz98765432",
                "name": "URL Livestream",
                "channel": "URL Channel",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["youtube_video_id"] == "xyz98765432"
    
    @pytest.mark.asyncio
    async def test_create_livestream_duplicate_video_id(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
    ):
        """Should reject duplicate video ID."""
        response = await async_client.post(
            "/api/v1/admin/livestreams",
            headers=auth_headers,
            json={
                "youtube_video_id": sample_livestream.youtube_video_id,
                "name": "Duplicate",
                "channel": "Channel",
            },
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_livestream_missing_required_fields(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should reject missing required fields."""
        response = await async_client.post(
            "/api/v1/admin/livestreams",
            headers=auth_headers,
            json={
                "youtube_video_id": "abc12345678",
                # Missing name and channel
            },
        )
        
        assert response.status_code == 422


class TestGetLivestream:
    """Tests for GET /admin/livestreams/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_livestream_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
    ):
        """Should return livestream by ID."""
        response = await async_client.get(
            f"/api/v1/admin/livestreams/{sample_livestream.public_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == sample_livestream.public_id
        assert data["name"] == sample_livestream.name
    
    @pytest.mark.asyncio
    async def test_get_livestream_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 404 for non-existent ID."""
        response = await async_client.get(
            "/api/v1/admin/livestreams/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


class TestUpdateLivestream:
    """Tests for PUT /admin/livestreams/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_livestream_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
    ):
        """Should update livestream fields."""
        response = await async_client.put(
            f"/api/v1/admin/livestreams/{sample_livestream.public_id}",
            headers=auth_headers,
            json={
                "name": "Updated Name",
                "is_live": False,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Name"
        assert data["is_live"] is False
        # Channel should remain unchanged
        assert data["channel"] == sample_livestream.channel
    
    @pytest.mark.asyncio
    async def test_update_livestream_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 404 for non-existent ID."""
        response = await async_client.put(
            "/api/v1/admin/livestreams/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"name": "New Name"},
        )
        
        assert response.status_code == 404


class TestDeleteLivestream:
    """Tests for DELETE /admin/livestreams/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_livestream_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
    ):
        """Should delete livestream."""
        response = await async_client.delete(
            f"/api/v1/admin/livestreams/{sample_livestream.public_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await async_client.get(
            f"/api/v1/admin/livestreams/{sample_livestream.public_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_livestream_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 404 for non-existent ID."""
        response = await async_client.delete(
            "/api/v1/admin/livestreams/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


class TestViewershipHistory:
    """Tests for GET /admin/livestreams/{id}/history endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_history_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
        sample_viewership: list[ViewershipHistory],
    ):
        """Should return viewership history."""
        response = await async_client.get(
            f"/api/v1/admin/livestreams/{sample_livestream.public_id}/history",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert data["livestream_id"] == sample_livestream.public_id
        assert len(data["items"]) == len(sample_viewership)
    
    @pytest.mark.asyncio
    async def test_get_history_livestream_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 404 for non-existent livestream."""
        response = await async_client.get(
            "/api/v1/admin/livestreams/00000000-0000-0000-0000-000000000000/history",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_history_with_time_range(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_livestream: Livestream,
        sample_viewership: list[ViewershipHistory],
    ):
        """Should filter by time range."""
        response = await async_client.get(
            f"/api/v1/admin/livestreams/{sample_livestream.public_id}/history",
            headers=auth_headers,
            params={
                "start_time": "2020-01-01T00:00:00Z",
                "end_time": "2030-01-01T00:00:00Z",
            },
        )
        
        assert response.status_code == 200
