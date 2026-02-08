"""
Livestream Service
==================

Business logic for livestream operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.anomaly import AsyncAnomalyDetector, AnomalyConfig
from app.config import get_settings
from app.models import Livestream, ViewershipHistory
from app.schemas import (
    LivestreamCreate,
    LivestreamUpdate,
    LivestreamResponse,
    LivestreamRankedResponse,
    DownsampleInterval,
    DownsampledViewershipResponse,
    DOWNSAMPLE_SECONDS,
)
from app.services.cache_service import get_cache_service, CacheKeys
from app.services.youtube_service import get_youtube_service, YouTubeValidationError


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
    
    # Valid sort fields for get_all
    VALID_SORT_FIELDS = {'name', 'channel', 'is_live', 'created_at', 'updated_at', 'peak_viewers'}
    
    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        is_live: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> tuple[list[Livestream], int]:
        """
        Get all livestreams with pagination and optional filtering.
        
        Args:
            skip: Number of items to skip
            limit: Maximum items to return
            search: Optional search term for name or channel
            is_live: Optional filter by live status
            sort_by: Field to sort by (name, channel, is_live, created_at, updated_at, peak_viewers)
            sort_order: Sort order ('asc' or 'desc')
        
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
        
        # Determine sort column and order
        sort_field = sort_by if sort_by in self.VALID_SORT_FIELDS else 'created_at'
        sort_column = getattr(Livestream, sort_field)
        order_func = desc if sort_order != 'asc' else lambda x: x  # asc is default for columns
        
        # Get paginated items
        stmt = (
            base_query
            .order_by(order_func(sort_column))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        livestreams = list(result.scalars().all())
        
        return livestreams, total
    
    async def get_current_viewers_map(self, livestream_ids: list[int]) -> dict[int, int]:
        """
        Get the most recent viewer count for multiple livestreams.
        
        Args:
            livestream_ids: List of internal livestream IDs
        
        Returns:
            Dictionary mapping livestream_id to current viewer count
        """
        if not livestream_ids:
            return {}
        
        # Subquery to get the latest timestamp for each livestream
        latest_subq = (
            select(
                ViewershipHistory.livestream_id,
                func.max(ViewershipHistory.timestamp).label('max_ts')
            )
            .where(ViewershipHistory.livestream_id.in_(livestream_ids))
            .group_by(ViewershipHistory.livestream_id)
            .subquery()
        )
        
        # Get the viewcount from the latest record for each livestream
        stmt = (
            select(ViewershipHistory.livestream_id, ViewershipHistory.viewcount)
            .join(
                latest_subq,
                (ViewershipHistory.livestream_id == latest_subq.c.livestream_id) &
                (ViewershipHistory.timestamp == latest_subq.c.max_ts)
            )
        )
        
        result = await self.session.execute(stmt)
        return {row.livestream_id: row.viewcount for row in result}
    
    async def get_current_viewers(self, livestream_id: int) -> Optional[int]:
        """
        Get the most recent viewer count for a single livestream.
        
        Args:
            livestream_id: Internal livestream ID
        
        Returns:
            Current viewer count or None if no history exists
        """
        viewers_map = await self.get_current_viewers_map([livestream_id])
        return viewers_map.get(livestream_id)
    
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
        
        Fetches video metadata from YouTube API before creating.
        
        Args:
            data: Livestream creation data (only youtube_url required)
        
        Returns:
            Created livestream with metadata from YouTube
        
        Raises:
            ValueError: If YouTube video ID already exists or video not found
        """
        # Check for existing video ID
        existing = await self.get_by_youtube_id(data.youtube_video_id)
        if existing:
            raise ValueError(
                f"Livestream with YouTube ID '{data.youtube_video_id}' already exists"
            )
        
        # Fetch metadata from YouTube API
        youtube_service = get_youtube_service()
        video_info = None
        
        try:
            video_info = await youtube_service.validate_video_exists(data.youtube_video_id)
        except YouTubeValidationError as e:
            raise ValueError(str(e))
        
        # Use YouTube metadata if available, otherwise require user-provided data
        if video_info:
            name = video_info.title
            channel = video_info.channel_title
            is_live = video_info.is_live
        else:
            # YouTube API not configured - require name and channel from request
            if not data.name or not data.channel:
                raise ValueError(
                    "YouTube API key not configured. Please provide name and channel manually."
                )
            name = data.name
            channel = data.channel
            is_live = data.is_live if data.is_live is not None else False
        
        # Build URL from video ID
        url = f"https://www.youtube.com/watch?v={data.youtube_video_id}"
        
        livestream = Livestream(
            youtube_video_id=data.youtube_video_id,
            name=name,
            channel=channel,
            description=data.description,
            url=url,
            is_live=is_live,
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
        skip: int = 0,
        limit: int = 50,
        downsample: Optional[DownsampleInterval] = None,
    ) -> tuple[list[Union[ViewershipHistory, DownsampledViewershipResponse]], int]:
        """
        Get viewership history for a livestream.
        
        Args:
            livestream_id: Livestream ID
            start_time: Start of time range (optional, no default - returns all if not set)
            end_time: End of time range (optional, no default - returns all if not set)
            skip: Number of records to skip (for pagination)
            limit: Maximum records to return per page
            downsample: Optional downsampling interval (5m, 10m, 1hr)
        
        Returns:
            Tuple of (history records, total count)
        """
        # Build query filters
        base_filter = [ViewershipHistory.livestream_id == livestream_id]
        
        # Only add time filters if explicitly provided
        if start_time is not None:
            base_filter.append(ViewershipHistory.timestamp >= start_time)
        if end_time is not None:
            base_filter.append(ViewershipHistory.timestamp <= end_time)
        
        if downsample is not None:
            # Downsampled query with time binning
            return await self._get_downsampled_history(
                livestream_id=livestream_id,
                base_filter=base_filter,
                skip=skip,
                limit=limit,
                downsample=downsample,
            )
        
        # Get total count
        count_stmt = (
            select(func.count())
            .select_from(ViewershipHistory)
            .where(*base_filter)
        )
        total = await self.session.scalar(count_stmt) or 0
        
        # Get records with pagination
        stmt = (
            select(ViewershipHistory)
            .where(*base_filter)
            .order_by(ViewershipHistory.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        history = list(result.scalars().all())
        
        return history, total
    
    async def _get_downsampled_history(
        self,
        livestream_id: int,
        base_filter: list,
        skip: int,
        limit: int,
        downsample: DownsampleInterval,
    ) -> tuple[list[DownsampledViewershipResponse], int]:
        """
        Get downsampled viewership history using time binning.
        
        Aggregates raw data into time bins (5m, 10m, 1hr) and returns
        the average viewcount per bin.
        
        Args:
            livestream_id: Livestream ID
            base_filter: Pre-built filter conditions
            skip: Number of bins to skip
            limit: Maximum bins to return
            downsample: Downsampling interval
        
        Returns:
            Tuple of (downsampled records, total bin count)
        """
        interval_seconds = DOWNSAMPLE_SECONDS[downsample]
        interval_suffix = downsample.value
        
        # Build the time bin expression using UNIX_TIMESTAMP
        # time_bin = FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(timestamp) / interval) * interval)
        time_bin_expr = func.from_unixtime(
            func.floor(func.unix_timestamp(ViewershipHistory.timestamp) / interval_seconds) * interval_seconds
        )
        
        # Subquery to get distinct time bins for counting
        count_subq = (
            select(time_bin_expr.label('time_bin'))
            .where(*base_filter)
            .group_by(text('time_bin'))
            .subquery()
        )
        
        count_stmt = select(func.count()).select_from(count_subq)
        total = await self.session.scalar(count_stmt) or 0
        
        # Main query for aggregated data
        # We get min(id) for the bin to use as the base ID
        stmt = (
            select(
                func.min(ViewershipHistory.id).label('min_id'),
                ViewershipHistory.livestream_id,
                time_bin_expr.label('time_bin'),
                func.round(func.avg(ViewershipHistory.viewcount)).label('avg_viewcount'),
            )
            .where(*base_filter)
            .group_by(ViewershipHistory.livestream_id, text('time_bin'))
            .order_by(text('time_bin DESC'))
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        # Convert to response objects
        history = [
            DownsampledViewershipResponse(
                id=f"{row.min_id}_{interval_suffix}",
                livestream_id=row.livestream_id,
                timestamp=row.time_bin,
                viewcount=int(row.avg_viewcount or 0),
            )
            for row in rows
        ]
        
        return history, total
    
    async def get_trending(
        self, 
        count: int = 10, 
        experimental: bool = False,
    ) -> list[LivestreamRankedResponse]:
        """
        Get trending livestreams ranked by anomaly/trend score.
        
        Uses anomaly detection to identify streams with unusual
        viewership patterns (spikes) and ranks by trend score.
        
        Args:
            count: Number of items to return (max 100)
            experimental: If True, bypass cache and use DB-stored config
        
        Returns:
            List of ranked livestreams with viewer data and trend scores
        """
        # Check cache first (skip if experimental mode)
        if not experimental:
            cached = self.cache.get(CacheKeys.TRENDING_LIVESTREAMS)
            if cached and not cached.is_expired:
                # Return requested count from cached data
                return cached.data[:count]
        
        # Configure anomaly detector
        if experimental:
            # Use config from database for experimental mode
            from app.services.anomaly_config_service import AnomalyConfigService
            config_service = AnomalyConfigService(self.session)
            config = await config_service.build_anomaly_config()
        else:
            # Use settings for normal mode
            settings = get_settings()
            config = AnomalyConfig(
                algorithm=settings.anomaly_algorithm,
                recent_window_minutes=settings.anomaly_recent_window_minutes,
                baseline_hours=settings.anomaly_baseline_hours,
            )
        
        # Run anomaly detection
        detector = AsyncAnomalyDetector(self.session, config)
        scores = await detector.detect_all_live_streams(limit=100)
        
        # Build ranked response from anomaly scores
        ranked_items = [
            LivestreamRankedResponse(
                id=str(score.livestream_id),  # Will be replaced with public_id below
                youtube_video_id=score.youtube_video_id,
                name=score.name,
                channel=score.channel,
                url=f"https://www.youtube.com/watch?v={score.youtube_video_id}",
                is_live=True,
                current_viewers=score.current_viewcount or 0,
                rank=idx + 1,
                trend_score=round(score.score, 2),
            )
            for idx, score in enumerate(scores)
        ]
        
        # Fetch public_ids for the livestreams
        if ranked_items:
            livestream_ids = [score.livestream_id for score in scores]
            stmt = select(Livestream.id, Livestream.public_id).where(
                Livestream.id.in_(livestream_ids)
            )
            result = await self.session.execute(stmt)
            id_map = {row.id: str(row.public_id) for row in result}
            
            # Update the ranked items with public_ids
            for item, score in zip(ranked_items, scores):
                item.id = id_map.get(score.livestream_id, item.id)
        
        # Cache the results (only for non-experimental mode)
        if not experimental:
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
