"""
Job Scheduler
=============

APScheduler-based job scheduling for the worker service.
"""

import asyncio
import logging
import signal
from datetime import datetime
from typing import Optional, Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from worker.config import WorkerSettings, get_worker_settings
from worker.youtube_client import YouTubeClient
from worker.tasks import PollTask, CleanupTask


logger = logging.getLogger(__name__)


class WorkerScheduler:
    """
    Manages scheduled jobs for the worker service.
    
    Uses APScheduler to run periodic tasks:
    - Poll task: Fetches YouTube data at configured intervals
    - Cleanup task: Removes old data (runs after each poll)
    """
    
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        youtube_client: YouTubeClient,
        settings: Optional[WorkerSettings] = None,
    ):
        """
        Initialize the scheduler.
        
        Args:
            session_factory: SQLAlchemy async session factory
            youtube_client: YouTube API client
            settings: Worker settings
        """
        self.settings = settings or get_worker_settings()
        self.session_factory = session_factory
        self.youtube_client = youtube_client
        
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._poll_task: Optional[PollTask] = None
        self._cleanup_task: Optional[CleanupTask] = None
        self._running = False
        self._shutdown_event: Optional[asyncio.Event] = None
    
    def _create_scheduler(self) -> AsyncIOScheduler:
        """Create and configure the APScheduler instance."""
        scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine missed runs into one
                "max_instances": 1,  # Only one instance of each job at a time
                "misfire_grace_time": 60,  # Allow 60s grace for misfires
            },
        )
        
        # Add event listeners for logging
        scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED,
        )
        scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR,
        )
        
        return scheduler
    
    def _on_job_executed(self, event: JobExecutionEvent) -> None:
        """Handle successful job execution."""
        logger.debug(f"Job {event.job_id} executed successfully")
    
    def _on_job_error(self, event: JobExecutionEvent) -> None:
        """Handle job execution error."""
        logger.error(
            f"Job {event.job_id} failed with exception: {event.exception}",
            exc_info=event.exception,
        )
    
    async def _run_poll(self) -> None:
        """Execute the poll task."""
        if self._poll_task is None:
            self._poll_task = PollTask(
                self.session_factory,
                self.youtube_client,
                self.settings,
            )
        
        try:
            await self._poll_task.run()
        except Exception as e:
            logger.error(f"Poll task error: {e}", exc_info=True)
    
    async def _run_cleanup(self) -> None:
        """Execute the cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = CleanupTask(
                self.session_factory,
                self.settings,
            )
        
        try:
            await self._cleanup_task.run()
        except Exception as e:
            logger.error(f"Cleanup task error: {e}", exc_info=True)
    
    async def _run_poll_and_cleanup(self) -> None:
        """Execute both poll and cleanup tasks sequentially."""
        await self._run_poll()
        await self._run_cleanup()
    
    def start(self) -> None:
        """
        Start the scheduler and begin running jobs.
        
        Jobs will run immediately on start and then at configured intervals.
        """
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._scheduler = self._create_scheduler()
        
        # Add the combined poll + cleanup job
        self._scheduler.add_job(
            self._run_poll_and_cleanup,
            trigger=IntervalTrigger(minutes=self.settings.poll_interval_minutes),
            id="poll_and_cleanup",
            name="Poll YouTube API and cleanup old data",
            next_run_time=datetime.utcnow(),  # Run immediately
        )
        
        self._scheduler.start()
        self._running = True
        
        logger.info(
            f"Scheduler started. Poll interval: {self.settings.poll_interval_minutes} minutes"
        )
    
    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running or self._scheduler is None:
            return
        
        logger.info("Stopping scheduler...")
        self._scheduler.shutdown(wait=True)
        self._scheduler = None
        self._running = False
        logger.info("Scheduler stopped")
    
    async def run_once(self) -> dict:
        """
        Run poll and cleanup tasks once (useful for testing/manual runs).
        
        Returns:
            Summary of both operations
        """
        poll_task = PollTask(
            self.session_factory,
            self.youtube_client,
            self.settings,
        )
        cleanup_task = CleanupTask(
            self.session_factory,
            self.settings,
        )
        
        poll_summary = await poll_task.run()
        cleanup_summary = await cleanup_task.run()
        
        return {
            "poll": poll_summary,
            "cleanup": cleanup_summary,
        }
    
    async def run_forever(self) -> None:
        """
        Run the scheduler until interrupted.
        
        Sets up signal handlers for graceful shutdown.
        """
        self._shutdown_event = asyncio.Event()
        
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        
        def signal_handler(sig):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            self._shutdown_event.set()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        
        # Start the scheduler
        self.start()
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Cleanup
        self.stop()
    
    @property
    def is_running(self) -> bool:
        """Whether the scheduler is currently running."""
        return self._running
    
    @property
    def poll_task(self) -> Optional[PollTask]:
        """The current poll task instance."""
        return self._poll_task
    
    @property
    def cleanup_task(self) -> Optional[CleanupTask]:
        """The current cleanup task instance."""
        return self._cleanup_task


async def create_scheduler(
    engine: AsyncEngine,
    settings: Optional[WorkerSettings] = None,
) -> WorkerScheduler:
    """
    Factory function to create a configured scheduler.
    
    Args:
        engine: SQLAlchemy async engine
        settings: Worker settings
        
    Returns:
        Configured WorkerScheduler instance
    """
    settings = settings or get_worker_settings()
    
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    youtube_client = YouTubeClient(settings)
    await youtube_client.start()
    
    return WorkerScheduler(session_factory, youtube_client, settings)
