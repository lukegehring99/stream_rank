"""
Test Configuration and Fixtures
================================

Shared fixtures for API testing.
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, Livestream, ViewershipHistory, User
from app.main import app
from app.db import get_async_session
from app.config import get_settings


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
SYNC_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test session."""
    async_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with database override."""
    
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield async_session
    
    app.dependency_overrides[get_async_session] = override_get_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_livestream(async_session: AsyncSession) -> Livestream:
    """Create a sample livestream for testing."""
    livestream = Livestream(
        youtube_video_id="dQw4w9WgXcQ",
        name="Test Livestream",
        channel="Test Channel",
        description="A test livestream",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        is_live=True,
    )
    async_session.add(livestream)
    await async_session.commit()
    await async_session.refresh(livestream)
    return livestream


@pytest_asyncio.fixture
async def sample_viewership(
    async_session: AsyncSession,
    sample_livestream: Livestream,
) -> list[ViewershipHistory]:
    """Create sample viewership history."""
    history = []
    for i in range(5):
        record = ViewershipHistory(
            livestream_id=sample_livestream.id,
            timestamp=datetime.now(timezone.utc),
            viewcount=1000 + (i * 100),
        )
        async_session.add(record)
        history.append(record)
    
    await async_session.commit()
    for h in history:
        await async_session.refresh(h)
    
    return history


@pytest_asyncio.fixture
async def admin_user(async_session: AsyncSession) -> User:
    """Create an admin user for testing."""
    user = User(
        username="testadmin",
        password_hash="",
    )
    user.set_password("testpassword123")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(
    async_client: AsyncClient,
    admin_user: User,
) -> str:
    """Get an admin JWT token."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testadmin",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(admin_token: str) -> dict:
    """Get authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(autouse=True)
def mock_youtube_service():
    """Mock YouTube service for all tests to avoid real API calls."""
    mock_service = MagicMock()
    
    # Mock validate_video_exists to return None (API not configured behavior)
    mock_service.validate_video_exists = AsyncMock(return_value=None)
    
    with patch('app.services.livestream_service.get_youtube_service', return_value=mock_service):
        yield mock_service
