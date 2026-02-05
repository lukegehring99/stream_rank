"""Background tasks for polling and cleanup."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Livestream, ViewershipHistory
from worker.youtube_client import YouTubeClient, QuotaExceededError

logger = logging.getLogger(__name__)


async def poll_viewership(
    session: AsyncSession,
    youtube_client: YouTubeClient,
) -> int:
    """Poll YouTube API for current viewership and store results.
    
    Args:
        session: Database session
        youtube_client: YouTube API client
        
    Returns:
        Number of records inserted
    """
    # Get all livestreams
    result = await session.execute(select(Livestream))
    livestreams = result.scalars().all()
    
    if not livestreams:
        logger.info("No livestreams to poll")
        return 0
    
    # Map video IDs to livestream IDs
    video_id_map = {ls.youtube_video_id: ls for ls in livestreams}
    video_ids = list(video_id_map.keys())
    
    logger.info(f"Polling {len(video_ids)} livestreams")
    
    try:
        # Fetch stats from YouTube
        stats = await youtube_client.get_video_stats(video_ids)
        
        now = datetime.now(timezone.utc)
        records_inserted = 0
        
        for stat in stats:
            livestream = video_id_map.get(stat.video_id)
            if not livestream:
                continue
            
            # Update is_live status
            livestream.is_live = stat.is_live
            
            # Insert viewership record
            record = ViewershipHistory(
                livestream_id=livestream.id,
                timestamp=now,
                viewcount=stat.view_count,
            )
            session.add(record)
            records_inserted += 1
            
            logger.debug(
                f"Recorded {stat.view_count} viewers for '{livestream.name}' "
                f"(is_live={stat.is_live})"
            )
        
        await session.commit()
        logger.info(f"Inserted {records_inserted} viewership records")
        
        return records_inserted
    
    except QuotaExceededError:
        logger.error("YouTube API quota exceeded - skipping this poll cycle")
        return 0
    
    except Exception as e:
        logger.error(f"Error polling viewership: {e}")
        await session.rollback()
        return 0


async def cleanup_old_data(
    session: AsyncSession,
    retention_days: int = 30,
    chunk_size: int = 1000,
) -> int:
    """Delete viewership history older than retention period.
    
    Uses chunked deletes to avoid long-running transactions.
    
    Args:
        session: Database session
        retention_days: Number of days to retain data
        chunk_size: Number of records to delete per chunk
        
    Returns:
        Total number of records deleted
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    total_deleted = 0
    
    logger.info(f"Cleaning up viewership data older than {cutoff}")
    
    while True:
        # Find IDs to delete
        result = await session.execute(
            select(ViewershipHistory.id)
            .where(ViewershipHistory.timestamp < cutoff)
            .limit(chunk_size)
        )
        ids_to_delete = [row[0] for row in result.fetchall()]
        
        if not ids_to_delete:
            break
        
        # Delete the chunk
        await session.execute(
            delete(ViewershipHistory).where(ViewershipHistory.id.in_(ids_to_delete))
        )
        await session.commit()
        
        total_deleted += len(ids_to_delete)
        logger.debug(f"Deleted {len(ids_to_delete)} records (total: {total_deleted})")
        
        # If we got fewer than chunk_size, we're done
        if len(ids_to_delete) < chunk_size:
            break
    
    if total_deleted > 0:
        logger.info(f"Cleaned up {total_deleted} old viewership records")
    
    return total_deleted
