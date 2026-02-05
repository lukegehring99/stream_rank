"""
Test fixtures for worker tests.
"""

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.models import Base, Livestream, ViewershipHistory
from worker.config import WorkerSettings
from worker.youtube_client import YouTubeClient, VideoStats


@pytest.fixture
def worker_settings(monkeypatch) -> WorkerSettings:
    """Create test worker settings."""
    # Set environment variables for pydantic-settings
    monkeypatch.setenv("YOUTUBE_API_KEY", "test_api_key_1234567890")
    monkeypatch.setenv("POLL_INTERVAL_MINUTES", "1")
    monkeypatch.setenv("RETENTION_DAYS", "30")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    # Clear the lru_cache to ensure fresh settings
    from worker.config import get_worker_settings
    get_worker_settings.cache_clear()
    
    return WorkerSettings(
        max_retries=2,
        initial_backoff_seconds=0.1,  # Minimum allowed
        max_backoff_seconds=1.0,  # Minimum allowed
        cleanup_batch_size=100,
        youtube_batch_size=50,
    )


@pytest_asyncio.fixture
async def async_engine(worker_settings: WorkerSettings) -> AsyncGenerator[AsyncEngine, None]:
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def sample_livestreams(
    db_session: AsyncSession,
) -> list[Livestream]:
    """Create sample livestreams in the database."""
    livestreams = [
        Livestream(
            youtube_video_id="abc12345678",
            name="Test Stream 1",
            channel="Test Channel 1",
            url="https://youtube.com/watch?v=abc12345678",
            is_live=True,
        ),
        Livestream(
            youtube_video_id="def87654321",
            name="Test Stream 2",
            channel="Test Channel 2",
            url="https://youtube.com/watch?v=def87654321",
            is_live=False,
        ),
        Livestream(
            youtube_video_id="ghi11223344",
            name="Test Stream 3",
            channel="Test Channel 3",
            url="https://youtube.com/watch?v=ghi11223344",
            is_live=True,
        ),
    ]
    
    for ls in livestreams:
        db_session.add(ls)
    
    await db_session.commit()
    
    # Refresh to get IDs
    for ls in livestreams:
        await db_session.refresh(ls)
    
    return livestreams


@pytest_asyncio.fixture
async def sample_viewership_history(
    db_session: AsyncSession,
    sample_livestreams: list[Livestream],
) -> list[ViewershipHistory]:
    """Create sample viewership history data."""
    now = datetime.utcnow()
    history = []
    
    for ls in sample_livestreams:
        # Create history for the past 45 days
        for days_ago in range(45):
            for hour in [0, 6, 12, 18]:
                timestamp = now - timedelta(days=days_ago, hours=hour)
                vh = ViewershipHistory(
                    livestream_id=ls.id,
                    timestamp=timestamp,
                    viewcount=1000 + (days_ago * 10) + hour,
                )
                history.append(vh)
                db_session.add(vh)
    
    await db_session.commit()
    return history


@pytest.fixture
def mock_youtube_client() -> YouTubeClient:
    """Create a mock YouTube client."""
    client = MagicMock(spec=YouTubeClient)
    client.start = AsyncMock()
    client.close = AsyncMock()
    client.get_videos_stats = AsyncMock(return_value=[])
    client.get_video_stats = AsyncMock(return_value=None)
    client.is_quota_exceeded = False
    client.request_count = 0
    return client


@pytest.fixture
def sample_video_stats() -> list[VideoStats]:
    """Create sample video stats."""
    return [
        VideoStats(
            video_id="abc12345678",
            view_count=15000,
            is_live=True,
            title="Test Stream 1",
            channel_title="Test Channel 1",
        ),
        VideoStats(
            video_id="def87654321",
            view_count=5000,
            is_live=False,
            title="Test Stream 2",
            channel_title="Test Channel 2",
        ),
        VideoStats(
            video_id="ghi11223344",
            view_count=25000,
            is_live=True,
            title="Test Stream 3",
            channel_title="Test Channel 3",
        ),
    ]
