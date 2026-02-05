"""
Worker Tasks
============

Async tasks for polling YouTube API and cleaning up old data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker

from app.models import Livestream, ViewershipHistory
from worker.config import WorkerSettings, get_worker_settings
from worker.youtube_client import YouTubeClient, QuotaExceededError, YouTubeAPIError


logger = logging.getLogger(__name__)


class PollTask:
    """
    Task for polling YouTube API and updating viewership data.
    
    Fetches current viewer counts for all tracked livestreams
    and records them in the database.
    """
    
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        youtube_client: YouTubeClient,
        settings: Optional[WorkerSettings] = None,
    ):
        """
        Initialize poll task.
        
        Args:
            session_factory: SQLAlchemy async session factory
            youtube_client: YouTube API client instance
            settings: Worker settings
        """
        self.session_factory = session_factory
        self.youtube_client = youtube_client
        self.settings = settings or get_worker_settings()
        self._last_run: Optional[datetime] = None
        self._run_count = 0
        self._error_count = 0
    
    async def run(self) -> dict:
        """
        Execute the poll task.
        
        Returns:
            Summary of the poll operation
        """
        start_time = datetime.utcnow()
        self._run_count += 1
        
        logger.info(f"Starting poll task (run #{self._run_count})")
        
        summary = {
            "started_at": start_time.isoformat(),
            "streams_processed": 0,
            "streams_updated": 0,
            "streams_now_live": 0,
            "streams_now_offline": 0,
            "errors": 0,
            "quota_exceeded": False,
        }
        
        try:
            async with self.session_factory() as session:
                # Get all tracked livestreams
                livestreams = await self._get_all_livestreams(session)
                
                if not livestreams:
                    logger.info("No livestreams to poll")
                    return summary
                
                logger.info(f"Polling {len(livestreams)} livestreams")
                
                # Get video IDs
                video_id_map = {ls.youtube_video_id: ls for ls in livestreams}
                video_ids = list(video_id_map.keys())
                
                # Fetch stats from YouTube API
                try:
                    stats_list = await self.youtube_client.get_videos_stats(video_ids)
                except QuotaExceededError:
                    logger.error("YouTube API quota exceeded, skipping poll")
                    summary["quota_exceeded"] = True
                    self._error_count += 1
                    return summary
                
                # Create a map of video_id -> stats
                stats_map = {s.video_id: s for s in stats_list}
                
                # Process each livestream
                now = datetime.utcnow()
                
                for video_id, livestream in video_id_map.items():
                    summary["streams_processed"] += 1
                    
                    stats = stats_map.get(video_id)
                    
                    if stats is None:
                        # Video not found - might be deleted or private
                        logger.warning(
                            f"Video {video_id} not found, marking as offline"
                        )
                        if livestream.is_live:
                            livestream.is_live = False
                            summary["streams_now_offline"] += 1
                        continue
                    
                    try:
                        # Update is_live status
                        was_live = livestream.is_live
                        livestream.is_live = stats.is_live
                        
                        if stats.is_live and not was_live:
                            summary["streams_now_live"] += 1
                            logger.info(f"Stream went live: {livestream.name}")
                        elif not stats.is_live and was_live:
                            summary["streams_now_offline"] += 1
                            logger.info(f"Stream went offline: {livestream.name}")
                        
                        # Update name and channel from YouTube if still placeholder
                        if livestream.name == "Loading..." and stats.title:
                            livestream.name = stats.title
                            logger.info(f"Updated stream name: {stats.title}")
                        if livestream.channel == "Loading..." and stats.channel_title:
                            livestream.channel = stats.channel_title
                            logger.info(f"Updated stream channel: {stats.channel_title}")
                        
                        # Update peak_viewers if current viewcount exceeds it
                        if stats.view_count > livestream.peak_viewers:
                            livestream.peak_viewers = stats.view_count
                            logger.debug(f"New peak viewers for {livestream.name}: {stats.view_count}")
                        
                        # Explicitly update updated_at timestamp
                        livestream.updated_at = now
                        
                        # Insert viewership history record
                        history = ViewershipHistory(
                            livestream_id=livestream.id,
                            timestamp=now,
                            viewcount=stats.view_count,
                        )
                        session.add(history)
                        summary["streams_updated"] += 1
                        
                        logger.debug(
                            f"Updated {livestream.name}: "
                            f"views={stats.view_count}, live={stats.is_live}"
                        )
                        
                    except Exception as e:
                        logger.error(
                            f"Error processing stream {video_id}: {e}",
                            exc_info=True,
                        )
                        summary["errors"] += 1
                        self._error_count += 1
                        # Continue with other streams
                        continue
                
                # Commit all changes
                await session.commit()
                
        except Exception as e:
            logger.error(f"Poll task failed: {e}", exc_info=True)
            summary["errors"] += 1
            self._error_count += 1
        
        self._last_run = datetime.utcnow()
        duration = (self._last_run - start_time).total_seconds()
        summary["duration_seconds"] = duration
        summary["completed_at"] = self._last_run.isoformat()
        
        logger.info(
            f"Poll task completed in {duration:.2f}s: "
            f"processed={summary['streams_processed']}, "
            f"updated={summary['streams_updated']}, "
            f"errors={summary['errors']}"
        )
        
        return summary
    
    async def _get_all_livestreams(
        self,
        session: AsyncSession,
    ) -> list[Livestream]:
        """Get all tracked livestreams from database."""
        stmt = select(Livestream).order_by(Livestream.id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @property
    def last_run(self) -> Optional[datetime]:
        """When the task last ran."""
        return self._last_run
    
    @property
    def run_count(self) -> int:
        """Total number of task runs."""
        return self._run_count
    
    @property
    def error_count(self) -> int:
        """Total number of errors encountered."""
        return self._error_count


class CleanupTask:
    """
    Task for cleaning up old viewership history data.
    
    Deletes records older than the configured retention period
    using chunked deletions to avoid long database locks.
    """
    
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Optional[WorkerSettings] = None,
    ):
        """
        Initialize cleanup task.
        
        Args:
            session_factory: SQLAlchemy async session factory
            settings: Worker settings
        """
        self.session_factory = session_factory
        self.settings = settings or get_worker_settings()
        self._last_run: Optional[datetime] = None
        self._total_deleted = 0
    
    async def run(self) -> dict:
        """
        Execute the cleanup task.
        
        Returns:
            Summary of the cleanup operation
        """
        start_time = datetime.utcnow()
        cutoff_date = start_time - timedelta(days=self.settings.retention_days)
        
        logger.info(
            f"Starting cleanup task: removing records older than "
            f"{cutoff_date.isoformat()} ({self.settings.retention_days} days)"
        )
        
        summary = {
            "started_at": start_time.isoformat(),
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": self.settings.retention_days,
            "total_deleted": 0,
            "batches": 0,
            "errors": 0,
        }
        
        try:
            total_deleted = 0
            batch_count = 0
            
            while True:
                async with self.session_factory() as session:
                    # Delete in batches to avoid long locks
                    # First, get IDs to delete
                    stmt = (
                        select(ViewershipHistory.id)
                        .where(ViewershipHistory.timestamp < cutoff_date)
                        .limit(self.settings.cleanup_batch_size)
                    )
                    result = await session.execute(stmt)
                    ids_to_delete = [row[0] for row in result.fetchall()]
                    
                    if not ids_to_delete:
                        # No more records to delete
                        break
                    
                    # Delete the batch
                    delete_stmt = (
                        delete(ViewershipHistory)
                        .where(ViewershipHistory.id.in_(ids_to_delete))
                    )
                    await session.execute(delete_stmt)
                    await session.commit()
                    
                    deleted_count = len(ids_to_delete)
                    total_deleted += deleted_count
                    batch_count += 1
                    
                    logger.debug(
                        f"Deleted batch {batch_count}: {deleted_count} records"
                    )
                    
                    # Small delay between batches to reduce database load
                    if deleted_count == self.settings.cleanup_batch_size:
                        await asyncio.sleep(0.1)
            
            summary["total_deleted"] = total_deleted
            summary["batches"] = batch_count
            self._total_deleted += total_deleted
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}", exc_info=True)
            summary["errors"] += 1
        
        self._last_run = datetime.utcnow()
        duration = (self._last_run - start_time).total_seconds()
        summary["duration_seconds"] = duration
        summary["completed_at"] = self._last_run.isoformat()
        
        logger.info(
            f"Cleanup task completed in {duration:.2f}s: "
            f"deleted={summary['total_deleted']} records in {summary['batches']} batches"
        )
        
        return summary
    
    @property
    def last_run(self) -> Optional[datetime]:
        """When the task last ran."""
        return self._last_run
    
    @property
    def total_deleted(self) -> int:
        """Total records deleted across all runs."""
        return self._total_deleted


async def run_poll_and_cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    youtube_client: YouTubeClient,
    settings: Optional[WorkerSettings] = None,
) -> dict:
    """
    Convenience function to run both poll and cleanup tasks.
    
    Args:
        session_factory: SQLAlchemy async session factory
        youtube_client: YouTube API client
        settings: Worker settings
        
    Returns:
        Combined summary of both operations
    """
    settings = settings or get_worker_settings()
    
    poll_task = PollTask(session_factory, youtube_client, settings)
    cleanup_task = CleanupTask(session_factory, settings)
    
    poll_summary = await poll_task.run()
    cleanup_summary = await cleanup_task.run()
    
    return {
        "poll": poll_summary,
        "cleanup": cleanup_summary,
    }
