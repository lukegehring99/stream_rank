"""
Livestream Service
==================

Business logic for livestream operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Livestream, ViewershipHistory
from app.schemas import (
    LivestreamCreate,
    LivestreamUpdate,
    LivestreamResponse,
    LivestreamRankedResponse,
)
from app.services.cache_service import get_cache_service, CacheKeys


class LivestreamService:
    """
    Service for managing livestream operations.
    
    Handles CRUD operations and ranking logic for livestreams.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the service with a database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
        self.cache = get_cache_service()
    
    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        is_live: Optional[bool] = None,
    ) -> tuple[list[Livestream], int]:
        """
        Get all livestreams with pagination and optional filtering.
        
        Args:
            skip: Number of items to skip
            limit: Maximum items to return
            search: Optional search term for name or channel
            is_live: Optional filter by live status
        
        Returns:
            Tuple of (livestreams list, total count)
        """
        # Build base query with filters
        base_query = select(Livestream)
        count_query = select(func.count()).select_from(Livestream)
        
        if search:
            search_filter = Livestream.name.ilike(f"%{search}%") | Livestream.channel.ilike(f"%{search}%")
            base_query = base_query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        if is_live is not None:
            base_query = base_query.where(Livestream.is_live == is_live)
            count_query = count_query.where(Livestream.is_live == is_live)
        
        # Get total count
        total = await self.session.scalar(count_query) or 0
        
        # Get paginated items
        stmt = (
            base_query
            .order_by(desc(Livestream.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        livestreams = list(result.scalars().all())
        
        return livestreams, total
    
    async def get_by_id(self, livestream_id: int) -> Optional[Livestream]:
        """
        Get a livestream by internal ID.
        
        Args:
            livestream_id: Livestream internal ID
        
        Returns:
            Livestream if found, None otherwise
        """
        stmt = select(Livestream).where(Livestream.id == livestream_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_public_id(self, public_id: str) -> Optional[Livestream]:
        """
        Get a livestream by public UUID.
        
        Args:
            public_id: Livestream public UUID
        
        Returns:
            Livestream if found, None otherwise
        """
        stmt = select(Livestream).where(Livestream.public_id == public_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_youtube_id(self, youtube_video_id: str) -> Optional[Livestream]:
        """
        Get a livestream by YouTube video ID.
        
        Args:
            youtube_video_id: YouTube video ID
        
        Returns:
            Livestream if found, None otherwise
        """
        stmt = select(Livestream).where(
            Livestream.youtube_video_id == youtube_video_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, data: LivestreamCreate) -> Livestream:
        """
        Create a new livestream.
        
        Args:
            data: Livestream creation data
        
        Returns:
            Created livestream
        
        Raises:
            ValueError: If YouTube video ID already exists
        """
        # Check for existing video ID
        existing = await self.get_by_youtube_id(data.youtube_video_id)
        if existing:
            raise ValueError(
                f"Livestream with YouTube ID '{data.youtube_video_id}' already exists"
            )
        
        # Build URL from video ID
        url = f"https://www.youtube.com/watch?v={data.youtube_video_id}"
        
        livestream = Livestream(
            youtube_video_id=data.youtube_video_id,
            name=data.name,
            channel=data.channel,
            description=data.description,
            url=url,
            is_live=data.is_live,
        )
        
        self.session.add(livestream)
        await self.session.flush()
        await self.session.refresh(livestream)
        
        # Invalidate trending cache
        self.cache.delete(CacheKeys.TRENDING_LIVESTREAMS)
        
        return livestream
    
    async def update(
        self, 
        livestream_id: int, 
        data: LivestreamUpdate,
    ) -> Optional[Livestream]:
        """
        Update a livestream by internal ID.
        
        Args:
            livestream_id: Livestream internal ID
            data: Update data (only non-None fields are updated)
        
        Returns:
            Updated livestream if found, None otherwise
        """
        livestream = await self.get_by_id(livestream_id)
        if not livestream:
            return None
        
        return await self._update_livestream(livestream, data)
    
    async def update_by_public_id(
        self, 
        public_id: str, 
        data: LivestreamUpdate,
    ) -> Optional[Livestream]:
        """
        Update a livestream by public UUID.
        
        Args:
            public_id: Livestream public UUID
            data: Update data (only non-None fields are updated)
        
        Returns:
            Updated livestream if found, None otherwise
        """
        livestream = await self.get_by_public_id(public_id)
        if not livestream:
            return None
        
        return await self._update_livestream(livestream, data)
    
    async def _update_livestream(
        self,
        livestream: Livestream,
        data: LivestreamUpdate,
    ) -> Livestream:
        """Internal method to update a livestream instance."""
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            setattr(livestream, field, value)
        
        await self.session.flush()
        await self.session.refresh(livestream)
        
        # Invalidate caches
        self.cache.delete(CacheKeys.TRENDING_LIVESTREAMS)
        self.cache.delete(CacheKeys.livestream(livestream.id))
        
        return livestream
    
    async def delete(self, livestream_id: int) -> bool:
        """
        Delete a livestream by internal ID.
        
        Args:
            livestream_id: Livestream internal ID
        
        Returns:
            True if deleted, False if not found
        """
        livestream = await self.get_by_id(livestream_id)
        if not livestream:
            return False
        
        await self.session.delete(livestream)
        await self.session.flush()
        
        # Invalidate caches
        self.cache.delete(CacheKeys.TRENDING_LIVESTREAMS)
        self.cache.delete(CacheKeys.livestream(livestream_id))
        
        return True
    
    async def delete_by_public_id(self, public_id: str) -> bool:
        """
        Delete a livestream by public UUID.
        
        Args:
            public_id: Livestream public UUID
        
        Returns:
            True if deleted, False if not found
        """
        livestream = await self.get_by_public_id(public_id)
        if not livestream:
            return False
        
        internal_id = livestream.id
        await self.session.delete(livestream)
        await self.session.flush()
        
        # Invalidate caches
        self.cache.delete(CacheKeys.TRENDING_LIVESTREAMS)
        self.cache.delete(CacheKeys.livestream(internal_id))
        
        return True
    
    async def get_viewership_history(
        self,
        livestream_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> tuple[list[ViewershipHistory], int]:
        """
        Get viewership history for a livestream.
        
        Args:
            livestream_id: Livestream ID
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)
            limit: Maximum records to return
        
        Returns:
            Tuple of (history records, total count)
        """
        # Default time range: last 24 hours
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(hours=24)
        
        # Build query
        base_filter = [
            ViewershipHistory.livestream_id == livestream_id,
            ViewershipHistory.timestamp >= start_time,
            ViewershipHistory.timestamp <= end_time,
        ]
        
        # Get total count
        count_stmt = (
            select(func.count())
            .select_from(ViewershipHistory)
            .where(*base_filter)
        )
        total = await self.session.scalar(count_stmt) or 0
        
        # Get records
        stmt = (
            select(ViewershipHistory)
            .where(*base_filter)
            .order_by(ViewershipHistory.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        history = list(result.scalars().all())
        
        return history, total
    
    async def get_trending(self, count: int = 10) -> list[LivestreamRankedResponse]:
        """
        Get trending livestreams with current viewer counts.
        
        Queries the most recent viewership data and ranks streams
        by current viewer count.
        
        Args:
            count: Number of items to return (max 100)
        
        Returns:
            List of ranked livestreams with viewer data
        """
        # Check cache first
        cached = self.cache.get(CacheKeys.TRENDING_LIVESTREAMS)
        if cached and not cached.is_expired:
            # Return requested count from cached data
            return cached.data[:count]
        
        # Subquery to get the latest viewership record for each livestream
        latest_viewership_subq = (
            select(
                ViewershipHistory.livestream_id,
                func.max(ViewershipHistory.timestamp).label("max_timestamp")
            )
            .group_by(ViewershipHistory.livestream_id)
            .subquery()
        )
        
        # Main query joining livestreams with their latest viewership
        stmt = (
            select(
                Livestream,
                ViewershipHistory.viewcount.label("current_viewers")
            )
            .join(
                latest_viewership_subq,
                Livestream.id == latest_viewership_subq.c.livestream_id
            )
            .join(
                ViewershipHistory,
                (ViewershipHistory.livestream_id == latest_viewership_subq.c.livestream_id) &
                (ViewershipHistory.timestamp == latest_viewership_subq.c.max_timestamp)
            )
            .where(Livestream.is_live == True)
            .order_by(desc("current_viewers"))
            .limit(100)  # Cache top 100
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        # Build ranked response
        ranked_items = [
            LivestreamRankedResponse(
                id=row.Livestream.public_id,
                youtube_video_id=row.Livestream.youtube_video_id,
                name=row.Livestream.name,
                channel=row.Livestream.channel,
                url=row.Livestream.url,
                is_live=row.Livestream.is_live,
                current_viewers=row.current_viewers or 0,
                rank=idx + 1,
            )
            for idx, row in enumerate(rows)
        ]
        
        # Cache the results
        self.cache.set(CacheKeys.TRENDING_LIVESTREAMS, ranked_items)
        
        return ranked_items[:count]

    async def get_dashboard_stats(self) -> dict:
        """
        Get aggregated statistics for the admin dashboard.
        
        Returns:
            Dictionary with total_streams, live_streams, total_viewers, peak_viewers_today
        """
        # Get total streams count
        total_stmt = select(func.count()).select_from(Livestream)
        total_streams = await self.session.scalar(total_stmt) or 0
        
        # Get live streams count
        live_stmt = select(func.count()).select_from(Livestream).where(
            Livestream.is_live == True
        )
        live_streams = await self.session.scalar(live_stmt) or 0
        
        # Get total current viewers - sum of most recent viewcount for each live stream
        # This subquery gets the latest viewership record for each livestream
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # Get sum of latest viewer counts for live streams
        latest_subq = (
            select(
                ViewershipHistory.livestream_id,
                func.max(ViewershipHistory.timestamp).label('max_ts')
            )
            .where(ViewershipHistory.timestamp >= today_start)
            .group_by(ViewershipHistory.livestream_id)
            .subquery()
        )
        
        viewers_stmt = (
            select(func.coalesce(func.sum(ViewershipHistory.viewcount), 0))
            .join(
                latest_subq,
                (ViewershipHistory.livestream_id == latest_subq.c.livestream_id) &
                (ViewershipHistory.timestamp == latest_subq.c.max_ts)
            )
            .join(Livestream, Livestream.id == ViewershipHistory.livestream_id)
            .where(Livestream.is_live == True)
        )
        total_viewers = await self.session.scalar(viewers_stmt) or 0
        
        # Get peak viewers today from viewership history
        peak_stmt = select(func.coalesce(func.max(ViewershipHistory.viewcount), 0)).where(
            ViewershipHistory.timestamp >= today_start
        )
        peak_viewers_today = await self.session.scalar(peak_stmt) or 0
        
        return {
            "total_streams": total_streams,
            "live_streams": live_streams,
            "total_viewers": int(total_viewers),
            "peak_viewers_today": int(peak_viewers_today),
        }


async def get_livestream_service(session: AsyncSession) -> LivestreamService:
    """
    Factory function for LivestreamService.
    
    Used with FastAPI's dependency injection.
    
    Args:
        session: Async SQLAlchemy session
    
    Returns:
        LivestreamService instance
    """
    return LivestreamService(session)
