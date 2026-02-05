"""
Tests for worker scheduler.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine

from worker.config import WorkerSettings
from worker.scheduler import WorkerScheduler, create_scheduler
from worker.youtube_client import YouTubeClient


class TestWorkerScheduler:
    """Tests for WorkerScheduler class."""
    
    @pytest.mark.asyncio
    async def test_start_and_stop(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
    ):
        """Test scheduler start and stop."""
        scheduler = WorkerScheduler(
            session_factory,
            mock_youtube_client,
            worker_settings,
        )
        
        assert scheduler.is_running is False
        
        scheduler.start()
        assert scheduler.is_running is True
        
        scheduler.stop()
        assert scheduler.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_twice_warning(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
        caplog,
    ):
        """Test that starting twice logs a warning."""
        scheduler = WorkerScheduler(
            session_factory,
            mock_youtube_client,
            worker_settings,
        )
        
        scheduler.start()
        scheduler.start()  # Second start
        
        assert "already running" in caplog.text.lower()
        
        scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_run_once(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
    ):
        """Test run_once method."""
        scheduler = WorkerScheduler(
            session_factory,
            mock_youtube_client,
            worker_settings,
        )
        
        summary = await scheduler.run_once()
        
        assert "poll" in summary
        assert "cleanup" in summary
    
    @pytest.mark.asyncio
    async def test_task_accessors(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mock_youtube_client,
        worker_settings: WorkerSettings,
    ):
        """Test task property accessors."""
        scheduler = WorkerScheduler(
            session_factory,
            mock_youtube_client,
            worker_settings,
        )
        
        # Initially None
        assert scheduler.poll_task is None
        assert scheduler.cleanup_task is None
        
        # After running once, tasks are created
        await scheduler.run_once()
        
        # Still None because run_once creates new tasks
        # The properties track tasks from scheduled runs
        assert scheduler.poll_task is None


class TestCreateScheduler:
    """Tests for create_scheduler factory function."""
    
    @pytest.mark.asyncio
    async def test_creates_scheduler(
        self,
        async_engine: AsyncEngine,
        worker_settings: WorkerSettings,
    ):
        """Test scheduler creation."""
        with patch.object(YouTubeClient, 'start', new_callable=AsyncMock):
            scheduler = await create_scheduler(async_engine, worker_settings)
        
        assert scheduler is not None
        assert isinstance(scheduler, WorkerScheduler)
        
        # Cleanup
        await scheduler.youtube_client.close()


class TestSchedulerIntegration:
    """Integration tests for scheduler."""
    
    @pytest.mark.asyncio
    async def test_scheduler_creates_jobs(self, worker_settings, session_factory, mock_youtube_client):
        """Test that scheduler creates the expected jobs."""
        scheduler = WorkerScheduler(
            session_factory,
            mock_youtube_client,
            worker_settings,
        )
        
        # Start should create jobs
        scheduler.start()
        assert scheduler.is_running is True
        
        # Verify APScheduler has jobs
        assert scheduler._scheduler is not None
        jobs = scheduler._scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "poll_and_cleanup"
        
        scheduler.stop()
