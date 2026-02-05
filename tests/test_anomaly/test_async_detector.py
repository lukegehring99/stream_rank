"""
Tests for AsyncAnomalyDetector.
================================

Tests the async anomaly detection functionality for FastAPI integration.
"""

import pytest
import pytest_asyncio
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Livestream, ViewershipHistory
from app.anomaly import (
    AsyncAnomalyDetector,
    AnomalyConfig,
    AnomalyScore,
    AnomalyStatus,
)


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create async test session."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def sample_livestream(async_session: AsyncSession) -> Livestream:
    """Create a sample livestream for testing."""
    livestream = Livestream(
        youtube_video_id="test123abc",
        name="Test Livestream",
        channel="Test Channel",
        url="https://www.youtube.com/watch?v=test123abc",
        is_live=True,
    )
    async_session.add(livestream)
    await async_session.flush()
    await async_session.refresh(livestream)
    return livestream


@pytest_asyncio.fixture
async def livestream_with_history(
    async_session: AsyncSession,
    sample_livestream: Livestream,
) -> Livestream:
    """Create a livestream with viewership history."""
    now = datetime.now(timezone.utc)
    
    # Create baseline data (24 hours of data, every 5 minutes)
    baseline_count = 100
    for i in range(baseline_count):
        timestamp = now - timedelta(hours=24) + timedelta(minutes=i * 5)
        # Stable baseline around 1000 viewers with some noise
        viewcount = 1000 + int(np.random.normal(0, 50))
        
        record = ViewershipHistory(
            livestream_id=sample_livestream.id,
            viewcount=max(viewcount, 0),
            timestamp=timestamp,
        )
        async_session.add(record)
    
    # Create recent spike (last 15 minutes with elevated viewers)
    for i in range(5):
        timestamp = now - timedelta(minutes=15) + timedelta(minutes=i * 3)
        viewcount = 5000 + int(np.random.normal(0, 100))  # 5x spike
        
        record = ViewershipHistory(
            livestream_id=sample_livestream.id,
            viewcount=viewcount,
            timestamp=timestamp,
        )
        async_session.add(record)
    
    await async_session.flush()
    return sample_livestream


class TestAsyncAnomalyDetector:
    """Tests for AsyncAnomalyDetector class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, async_session: AsyncSession):
        """Test detector initialization with defaults."""
        detector = AsyncAnomalyDetector(async_session)
        
        assert detector.session == async_session
        assert detector.config is not None
        assert detector.strategy is not None
    
    @pytest.mark.asyncio
    async def test_initialization_with_config(self, async_session: AsyncSession):
        """Test detector initialization with custom config."""
        config = AnomalyConfig(
            algorithm="zscore",
            recent_window_minutes=30,
            baseline_hours=48,
        )
        
        detector = AsyncAnomalyDetector(async_session, config)
        
        assert detector.config.algorithm == "zscore"
        assert detector.config.recent_window_minutes == 30
        assert detector.config.baseline_hours == 48
    
    @pytest.mark.asyncio
    async def test_detect_all_live_streams_empty(self, async_session: AsyncSession):
        """Test detection with no live streams."""
        detector = AsyncAnomalyDetector(async_session)
        
        scores = await detector.detect_all_live_streams()
        
        assert scores == []
    
    @pytest.mark.asyncio
    async def test_detect_all_live_streams_no_history(
        self,
        async_session: AsyncSession,
        sample_livestream: Livestream,
    ):
        """Test detection with livestream but no viewership history."""
        detector = AsyncAnomalyDetector(async_session)
        
        scores = await detector.detect_all_live_streams()
        
        assert len(scores) == 1
        assert scores[0].livestream_id == sample_livestream.id
        assert scores[0].status == AnomalyStatus.INACTIVE
    
    @pytest.mark.asyncio
    async def test_detect_all_live_streams_with_history(
        self,
        async_session: AsyncSession,
        livestream_with_history: Livestream,
    ):
        """Test detection with viewership history."""
        detector = AsyncAnomalyDetector(async_session)
        
        scores = await detector.detect_all_live_streams()
        
        assert len(scores) == 1
        score = scores[0]
        
        assert score.livestream_id == livestream_with_history.id
        assert score.youtube_video_id == livestream_with_history.youtube_video_id
        assert score.name == livestream_with_history.name
        assert score.channel == livestream_with_history.channel
        assert score.score >= 0
        assert score.current_viewcount is not None
    
    @pytest.mark.asyncio
    async def test_detect_for_stream(
        self,
        async_session: AsyncSession,
        livestream_with_history: Livestream,
    ):
        """Test detection for a single stream."""
        detector = AsyncAnomalyDetector(async_session)
        
        score = await detector.detect_for_stream(livestream_with_history)
        
        assert score.livestream_id == livestream_with_history.id
        assert score.name == livestream_with_history.name
        assert score.channel == livestream_with_history.channel
    
    @pytest.mark.asyncio
    async def test_detect_with_limit(
        self,
        async_session: AsyncSession,
    ):
        """Test detection with limit parameter."""
        # Create multiple livestreams
        for i in range(5):
            livestream = Livestream(
                youtube_video_id=f"video{i:03d}",
                name=f"Stream {i}",
                channel=f"Channel {i}",
                url=f"https://www.youtube.com/watch?v=video{i:03d}",
                is_live=True,
            )
            async_session.add(livestream)
        
        await async_session.flush()
        
        detector = AsyncAnomalyDetector(async_session)
        
        # Request only 3
        scores = await detector.detect_all_live_streams(limit=3)
        
        assert len(scores) == 3
    
    @pytest.mark.asyncio
    async def test_scores_sorted_by_score_descending(
        self,
        async_session: AsyncSession,
    ):
        """Test that scores are sorted by score descending."""
        # Create multiple livestreams with different histories
        now = datetime.now(timezone.utc)
        
        for i in range(3):
            livestream = Livestream(
                youtube_video_id=f"sort{i:03d}",
                name=f"Stream {i}",
                channel=f"Channel {i}",
                url=f"https://www.youtube.com/watch?v=sort{i:03d}",
                is_live=True,
            )
            async_session.add(livestream)
            await async_session.flush()
            
            # Add some viewership data
            for j in range(10):
                record = ViewershipHistory(
                    livestream_id=livestream.id,
                    viewcount=100 * (i + 1),  # Different viewer levels
                    timestamp=now - timedelta(minutes=j * 5),
                )
                async_session.add(record)
        
        await async_session.flush()
        
        detector = AsyncAnomalyDetector(async_session)
        scores = await detector.detect_all_live_streams()
        
        # Verify sorted by score descending
        for i in range(len(scores) - 1):
            assert scores[i].score >= scores[i + 1].score


class TestAsyncDetectorDataFetching:
    """Tests for async data fetching methods."""
    
    @pytest.mark.asyncio
    async def test_fetch_viewership_data_empty(
        self,
        async_session: AsyncSession,
        sample_livestream: Livestream,
    ):
        """Test fetching viewership data when none exists."""
        detector = AsyncAnomalyDetector(async_session)
        
        now = datetime.now(timezone.utc)
        data = await detector._fetch_viewership_data(
            livestream=sample_livestream,
            start_time=now - timedelta(hours=24),
            end_time=now,
        )
        
        assert data.is_empty
        assert data.livestream_id == sample_livestream.id
        assert data.youtube_video_id == sample_livestream.youtube_video_id
        assert data.name == sample_livestream.name
        assert data.channel == sample_livestream.channel
    
    @pytest.mark.asyncio
    async def test_fetch_viewership_data_with_records(
        self,
        async_session: AsyncSession,
        livestream_with_history: Livestream,
    ):
        """Test fetching viewership data with existing records."""
        detector = AsyncAnomalyDetector(async_session)
        
        now = datetime.now(timezone.utc)
        data = await detector._fetch_viewership_data(
            livestream=livestream_with_history,
            start_time=now - timedelta(hours=24),
            end_time=now,
        )
        
        assert not data.is_empty
        assert data.sample_count > 0
        assert data.latest_viewcount is not None
        assert data.latest_timestamp is not None
