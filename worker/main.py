#!/usr/bin/env python3
"""
Background Worker Service Entry Point
=====================================

Standalone service for polling YouTube API and maintaining
viewership data. Run as a separate process from the API server.

Usage:
    # Run the worker service
    python -m worker.main
    
    # Or with environment variables
    YOUTUBE_API_KEY=your_key POLL_INTERVAL_MINUTES=5 python -m worker.main
    
    # Run once (for testing/cron)
    python -m worker.main --once
"""

import argparse
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    AsyncSession,
)

from worker.config import get_worker_settings, WorkerSettings
from worker.youtube_client import YouTubeClient
from worker.scheduler import WorkerScheduler
from worker.tasks import PollTask, CleanupTask


def setup_logging(settings: WorkerSettings) -> None:
    """Configure logging for the worker service."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)


def create_engine(settings: WorkerSettings) -> AsyncEngine:
    """Create the async database engine."""
    return create_async_engine(
        settings.async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        echo=False,
    )


@asynccontextmanager
async def create_resources(
    settings: WorkerSettings,
) -> AsyncGenerator[tuple[AsyncEngine, YouTubeClient], None]:
    """
    Create and manage worker resources.
    
    Yields:
        Tuple of (engine, youtube_client)
    """
    logger = logging.getLogger(__name__)
    
    # Create database engine
    engine = create_engine(settings)
    logger.info("Database engine created")
    
    # Create YouTube client
    youtube_client = YouTubeClient(settings)
    await youtube_client.start()
    logger.info("YouTube client started")
    
    try:
        yield engine, youtube_client
    finally:
        # Cleanup
        await youtube_client.close()
        await engine.dispose()
        logger.info("Resources cleaned up")


async def run_scheduled(settings: WorkerSettings) -> None:
    """Run the worker with scheduled jobs."""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Starting Background Worker Service")
    logger.info("=" * 60)
    logger.info(f"Poll interval: {settings.poll_interval_minutes} minutes")
    logger.info(f"Retention period: {settings.retention_days} days")
    logger.info(f"Log level: {settings.log_level}")
    logger.info("=" * 60)
    
    async with create_resources(settings) as (engine, youtube_client):
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        scheduler = WorkerScheduler(
            session_factory=session_factory,
            youtube_client=youtube_client,
            settings=settings,
        )
        
        await scheduler.run_forever()
    
    logger.info("Worker service shut down complete")


async def run_once(settings: WorkerSettings) -> None:
    """Run the poll and cleanup tasks once."""
    logger = logging.getLogger(__name__)
    
    logger.info("Running worker tasks once...")
    
    async with create_resources(settings) as (engine, youtube_client):
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        poll_task = PollTask(
            session_factory=session_factory,
            youtube_client=youtube_client,
            settings=settings,
        )
        
        cleanup_task = CleanupTask(
            session_factory=session_factory,
            settings=settings,
        )
        
        # Run poll
        poll_summary = await poll_task.run()
        logger.info(f"Poll summary: {poll_summary}")
        
        # Run cleanup
        cleanup_summary = await cleanup_task.run()
        logger.info(f"Cleanup summary: {cleanup_summary}")
    
    logger.info("Single run complete")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Background worker for Trending YouTube Livestreams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  YOUTUBE_API_KEY        YouTube Data API v3 key (required)
  POLL_INTERVAL_MINUTES  How often to poll (default: 3)
  RETENTION_DAYS         Days to keep history (default: 30)
  DATABASE_URL           Database connection URL
  LOG_LEVEL              Logging level (default: INFO)

Examples:
  # Run as continuous service
  python -m worker.main
  
  # Run once (for testing or cron)
  python -m worker.main --once
  
  # With custom settings
  POLL_INTERVAL_MINUTES=5 python -m worker.main
        """,
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run poll and cleanup once, then exit",
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit",
    )
    
    return parser.parse_args()


def validate_config() -> bool:
    """Validate configuration and print status."""
    logger = logging.getLogger(__name__)
    
    try:
        settings = get_worker_settings()
        
        print("Configuration validated successfully!")
        print(f"  YouTube API Key: {'*' * 8}...{settings.youtube_api_key[-4:]}")
        print(f"  Poll Interval: {settings.poll_interval_minutes} minutes")
        print(f"  Retention Days: {settings.retention_days}")
        print(f"  Database URL: {settings.database_url[:30]}...")
        print(f"  Log Level: {settings.log_level}")
        
        return True
        
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return False


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Handle config validation
    if args.validate_config:
        return 0 if validate_config() else 1
    
    # Load settings (will raise if invalid)
    try:
        settings = get_worker_settings()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nMake sure YOUTUBE_API_KEY is set!", file=sys.stderr)
        return 1
    
    # Setup logging
    setup_logging(settings)
    logger = logging.getLogger(__name__)
    
    try:
        if args.once:
            asyncio.run(run_once(settings))
        else:
            asyncio.run(run_scheduled(settings))
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        return 0
        
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
