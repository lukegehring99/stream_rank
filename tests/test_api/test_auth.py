"""
Authentication API Tests
========================

Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models import User


class TestLoginEndpoint:
    """Tests for /auth/login endpoint."""
    
    @pytest.mark.asyncio
    async def test_login_success(
        self,
        async_client: AsyncClient,
        admin_user: User,
    ):
        """Should return token on valid credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "testadmin",
                "password": "testpassword123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "username" in data
        
        assert data["token_type"] == "bearer"
        assert data["username"] == "testadmin"
        assert data["expires_in"] > 0
    
    @pytest.mark.asyncio
    async def test_login_invalid_username(
        self,
        async_client: AsyncClient,
        admin_user: User,
    ):
        """Should return 401 on invalid username."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "wronguser",
                "password": "testpassword123",
            },
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        async_client: AsyncClient,
        admin_user: User,
    ):
        """Should return 401 on invalid password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "testadmin",
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_missing_username(self, async_client: AsyncClient):
        """Should return 422 on missing username."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"password": "testpassword123"},
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_missing_password(self, async_client: AsyncClient):
        """Should return 422 on missing password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin"},
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_empty_body(self, async_client: AsyncClient):
        """Should return 422 on empty body."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={},
        )
        
        assert response.status_code == 422
