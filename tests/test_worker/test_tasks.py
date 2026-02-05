"""
Tests for worker tasks.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Livestream, ViewershipHistory
from worker.config import WorkerSettings
from worker.youtube_client import VideoStats, QuotaExceededError
from worker.tasks import PollTask, CleanupTask, run_poll_and_cleanup


class TestPollTask:
    """Tests for PollTask class."""
    
    @pytest.mark.asyncio
    async def test_run_no_livestreams(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
    ):
        """Test poll with no livestreams in database."""
        task = PollTask(session_factory, mock_youtube_client, worker_settings)
        
        summary = await task.run()
        
        assert summary["streams_processed"] == 0
        assert summary["streams_updated"] == 0
        assert task.run_count == 1
        mock_youtube_client.get_videos_stats.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_with_livestreams(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
        sample_livestreams: list[Livestream],
        sample_video_stats: list[VideoStats],
    ):
        """Test poll with livestreams."""
        mock_youtube_client.get_videos_stats = AsyncMock(
            return_value=sample_video_stats
        )
        
        task = PollTask(session_factory, mock_youtube_client, worker_settings)
        summary = await task.run()
        
        assert summary["streams_processed"] == 3
        assert summary["streams_updated"] == 3
        assert summary["errors"] == 0
        
        # Verify viewership history was created
        async with session_factory() as session:
            count_result = await session.execute(
                select(func.count(ViewershipHistory.id))
            )
            count = count_result.scalar()
            assert count == 3
    
    @pytest.mark.asyncio
    async def test_run_updates_is_live_status(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
        sample_livestreams: list[Livestream],
    ):
        """Test that is_live status is updated correctly."""
        # Stream 1 was live, now offline
        # Stream 2 was offline, now live
        # Stream 3 was live, still live
        stats = [
            VideoStats(
                video_id="abc12345678",
                view_count=1000,
                is_live=False,  # Was True
            ),
            VideoStats(
                video_id="def87654321",
                view_count=2000,
                is_live=True,  # Was False
            ),
            VideoStats(
                video_id="ghi11223344",
                view_count=3000,
                is_live=True,  # Still True
            ),
        ]
        
        mock_youtube_client.get_videos_stats = AsyncMock(return_value=stats)
        
        task = PollTask(session_factory, mock_youtube_client, worker_settings)
        summary = await task.run()
        
        assert summary["streams_now_live"] == 1
        assert summary["streams_now_offline"] == 1
        
        # Verify database was updated
        async with session_factory() as session:
            result = await session.execute(
                select(Livestream).where(Livestream.youtube_video_id == "abc12345678")
            )
            ls = result.scalar_one()
            assert ls.is_live is False
            
            result = await session.execute(
                select(Livestream).where(Livestream.youtube_video_id == "def87654321")
            )
            ls = result.scalar_one()
            assert ls.is_live is True
    
    @pytest.mark.asyncio
    async def test_run_handles_missing_video(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
        sample_livestreams: list[Livestream],
    ):
        """Test handling of videos not found in YouTube API."""
        # Only return stats for 2 of 3 videos
        stats = [
            VideoStats(video_id="abc12345678", view_count=1000, is_live=True),
            VideoStats(video_id="ghi11223344", view_count=3000, is_live=True),
        ]
        
        mock_youtube_client.get_videos_stats = AsyncMock(return_value=stats)
        
        task = PollTask(session_factory, mock_youtube_client, worker_settings)
        summary = await task.run()
        
        assert summary["streams_processed"] == 3
        assert summary["streams_updated"] == 2
    
    @pytest.mark.asyncio
    async def test_run_handles_quota_exceeded(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
        sample_livestreams: list[Livestream],
    ):
        """Test handling of quota exceeded error."""
        mock_youtube_client.get_videos_stats = AsyncMock(
            side_effect=QuotaExceededError("Quota exceeded")
        )
        
        task = PollTask(session_factory, mock_youtube_client, worker_settings)
        summary = await task.run()
        
        assert summary["quota_exceeded"] is True
        assert summary["streams_processed"] == 0
    
    @pytest.mark.asyncio
    async def test_task_properties(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
        sample_livestreams: list[Livestream],
        sample_video_stats: list[VideoStats],
    ):
        """Test task property accessors."""
        mock_youtube_client.get_videos_stats = AsyncMock(return_value=sample_video_stats)
        task = PollTask(session_factory, mock_youtube_client, worker_settings)
        
        assert task.last_run is None
        assert task.run_count == 0
        assert task.error_count == 0
        
        await task.run()
        
        assert task.last_run is not None
        assert task.run_count == 1


class TestCleanupTask:
    """Tests for CleanupTask class."""
    
    @pytest.mark.asyncio
    async def test_run_deletes_old_records(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_settings: WorkerSettings,
        sample_livestreams: list[Livestream],
        sample_viewership_history: list[ViewershipHistory],
    ):
        """Test that old records are deleted."""
        # Count records before cleanup
        async with session_factory() as session:
            result = await session.execute(
                select(func.count(ViewershipHistory.id))
            )
            count_before = result.scalar()
        
        task = CleanupTask(session_factory, worker_settings)
        summary = await task.run()
        
        assert summary["total_deleted"] > 0
        
        # Count records after cleanup
        async with session_factory() as session:
            result = await session.execute(
                select(func.count(ViewershipHistory.id))
            )
            count_after = result.scalar()
        
        assert count_after < count_before
    
    @pytest.mark.asyncio
    async def test_run_respects_retention_days(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        sample_livestreams: list[Livestream],
        monkeypatch,
    ):
        """Test that records within retention period are kept."""
        # Create settings with 7 day retention
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        monkeypatch.setenv("RETENTION_DAYS", "7")
        from worker.config import get_worker_settings
        get_worker_settings.cache_clear()
        
        settings = WorkerSettings(cleanup_batch_size=100)
        
        # Create history data
        now = datetime.utcnow()
        async with session_factory() as session:
            # Record from 5 days ago (should be kept)
            recent = ViewershipHistory(
                livestream_id=sample_livestreams[0].id,
                timestamp=now - timedelta(days=5),
                viewcount=1000,
            )
            # Record from 10 days ago (should be deleted)
            old = ViewershipHistory(
                livestream_id=sample_livestreams[0].id,
                timestamp=now - timedelta(days=10),
                viewcount=500,
            )
            session.add(recent)
            session.add(old)
            await session.commit()
        
        task = CleanupTask(session_factory, settings)
        summary = await task.run()
        
        assert summary["total_deleted"] == 1
        
        # Verify the recent record was kept
        async with session_factory() as session:
            result = await session.execute(
                select(ViewershipHistory).where(
                    ViewershipHistory.livestream_id == sample_livestreams[0].id
                )
            )
            remaining = result.scalars().all()
            assert len(remaining) == 1
            assert remaining[0].viewcount == 1000
    
    @pytest.mark.asyncio
    async def test_run_no_old_records(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_settings: WorkerSettings,
        sample_livestreams: list[Livestream],
    ):
        """Test cleanup with no old records."""
        # Create only recent records
        now = datetime.utcnow()
        async with session_factory() as session:
            vh = ViewershipHistory(
                livestream_id=sample_livestreams[0].id,
                timestamp=now - timedelta(days=1),
                viewcount=1000,
            )
            session.add(vh)
            await session.commit()
        
        task = CleanupTask(session_factory, worker_settings)
        summary = await task.run()
        
        assert summary["total_deleted"] == 0
        assert summary["batches"] == 0
    
    @pytest.mark.asyncio
    async def test_chunked_deletion(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        sample_livestreams: list[Livestream],
        monkeypatch,
    ):
        """Test that deletions are chunked."""
        # Create settings with small batch size
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        monkeypatch.setenv("RETENTION_DAYS", "7")
        from worker.config import get_worker_settings
        get_worker_settings.cache_clear()
        
        settings = WorkerSettings(cleanup_batch_size=10)
        
        # Create 25 old records
        now = datetime.utcnow()
        async with session_factory() as session:
            for i in range(25):
                vh = ViewershipHistory(
                    livestream_id=sample_livestreams[0].id,
                    timestamp=now - timedelta(days=30),
                    viewcount=i,
                )
                session.add(vh)
            await session.commit()
        
        task = CleanupTask(session_factory, settings)
        summary = await task.run()
        
        assert summary["total_deleted"] == 25
        assert summary["batches"] == 3  # 10 + 10 + 5
    
    @pytest.mark.asyncio
    async def test_task_properties(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        worker_settings: WorkerSettings,
    ):
        """Test task property accessors."""
        task = CleanupTask(session_factory, worker_settings)
        
        assert task.last_run is None
        assert task.total_deleted == 0
        
        await task.run()
        
        assert task.last_run is not None


class TestRunPollAndCleanup:
    """Tests for run_poll_and_cleanup function."""
    
    @pytest.mark.asyncio
    async def test_runs_both_tasks(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
    ):
        """Test that both tasks are run."""
        summary = await run_poll_and_cleanup(
            session_factory,
            mock_youtube_client,
            worker_settings,
        )
        
        assert "poll" in summary
        assert "cleanup" in summary
        assert "started_at" in summary["poll"]
        assert "started_at" in summary["cleanup"]
