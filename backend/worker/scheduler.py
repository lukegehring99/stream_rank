"""Worker scheduler using APScheduler."""
import asyncio
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from worker.config import WorkerSettings
from worker.youtube_client import YouTubeClient
from worker.tasks import poll_viewership, cleanup_old_data

logger = logging.getLogger(__name__)


class WorkerScheduler:
    """Manages background job scheduling."""
    
    def __init__(self, settings: WorkerSettings):
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self._engine = None
        self._session_factory: Optional[async_sessionmaker] = None
    
    def _setup_database(self) -> None:
        """Initialize database connection."""
        self._engine = create_async_engine(
            self.settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def _get_session(self) -> AsyncSession:
        """Get a database session."""
        if not self._session_factory:
            self._setup_database()
        return self._session_factory()
    
    async def poll_job(self) -> None:
        """Job to poll YouTube API and store viewership."""
        logger.info("Starting poll job")
        
        async with await self._get_session() as session:
            async with YouTubeClient(
                api_key=self.settings.youtube_api_key,
                max_retries=self.settings.max_retries,
                retry_delay=self.settings.retry_delay_seconds,
                batch_size=self.settings.youtube_batch_size,
            ) as client:
                await poll_viewership(session, client)
    
    async def cleanup_job(self) -> None:
        """Job to clean up old viewership data."""
        logger.info("Starting cleanup job")
        
        async with await self._get_session() as session:
            await cleanup_old_data(
                session,
                retention_days=self.settings.retention_days,
            )
    
    def start(self) -> None:
        """Start the scheduler."""
        # Validate API key
        if not self.settings.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable is required")
        
        self._setup_database()
        
        # Schedule poll job
        self.scheduler.add_job(
            self.poll_job,
            trigger=IntervalTrigger(minutes=self.settings.poll_interval_minutes),
            id="poll_viewership",
            name="Poll YouTube Viewership",
            replace_existing=True,
        )
        
        # Schedule cleanup job (run every 6 hours)
        self.scheduler.add_job(
            self.cleanup_job,
            trigger=IntervalTrigger(hours=6),
            id="cleanup_old_data",
            name="Cleanup Old Viewership Data",
            replace_existing=True,
        )
        
        logger.info(
            f"Starting scheduler with poll interval of {self.settings.poll_interval_minutes} minutes"
        )
        self.scheduler.start()
    
    async def run_once(self) -> None:
        """Run poll and cleanup once (for testing/cron)."""
        if not self.settings.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable is required")
        
        self._setup_database()
        
        await self.poll_job()
        await self.cleanup_job()
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    async def shutdown(self) -> None:
        """Shutdown and cleanup resources."""
        self.stop()
        if self._engine:
            await self._engine.dispose()
