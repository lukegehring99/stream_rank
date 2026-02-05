"""Livestream service for database operations."""
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Livestream, ViewershipHistory
from app.schemas.livestream import LivestreamCreate, LivestreamUpdate


class LivestreamService:
    """Service for livestream database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_live: Optional[bool] = None,
    ) -> Tuple[List[Livestream], int]:
        """Get all livestreams with pagination.
        
        Returns:
            Tuple of (livestreams, total_count)
        """
        # Build query
        query = select(Livestream)
        count_query = select(func.count(Livestream.id))
        
        if is_live is not None:
            query = query.where(Livestream.is_live == is_live)
            count_query = count_query.where(Livestream.is_live == is_live)
        
        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Livestream.created_at.desc())
        result = await self.session.execute(query)
        livestreams = result.scalars().all()
        
        return list(livestreams), total
    
    async def get_by_id(self, livestream_id: int) -> Optional[Livestream]:
        """Get a livestream by ID."""
        result = await self.session.execute(
            select(Livestream).where(Livestream.id == livestream_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_youtube_id(self, youtube_video_id: str) -> Optional[Livestream]:
        """Get a livestream by YouTube video ID."""
        result = await self.session.execute(
            select(Livestream).where(Livestream.youtube_video_id == youtube_video_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, data: LivestreamCreate) -> Livestream:
        """Create a new livestream."""
        # Extract video ID from URL or use directly
        video_id = self._extract_video_id(data.youtube_url_or_id)
        
        # Build YouTube URL
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        livestream = Livestream(
            youtube_video_id=video_id,
            name=data.name,
            channel=data.channel,
            description=data.description,
            url=url,
            is_live=True,
        )
        
        self.session.add(livestream)
        await self.session.flush()
        await self.session.refresh(livestream)
        
        return livestream
    
    async def update(
        self,
        livestream_id: int,
        data: LivestreamUpdate,
    ) -> Optional[Livestream]:
        """Update a livestream."""
        livestream = await self.get_by_id(livestream_id)
        if not livestream:
            return None
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(livestream, field, value)
        
        await self.session.flush()
        await self.session.refresh(livestream)
        
        return livestream
    
    async def delete(self, livestream_id: int) -> bool:
        """Delete a livestream and its history."""
        livestream = await self.get_by_id(livestream_id)
        if not livestream:
            return False
        
        await self.session.delete(livestream)
        await self.session.flush()
        
        return True
    
    async def get_viewership_history(
        self,
        livestream_id: int,
        hours: int = 24,
        limit: int = 1000,
    ) -> List[ViewershipHistory]:
        """Get viewership history for a livestream."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        result = await self.session.execute(
            select(ViewershipHistory)
            .where(
                and_(
                    ViewershipHistory.livestream_id == livestream_id,
                    ViewershipHistory.timestamp >= since,
                )
            )
            .order_by(ViewershipHistory.timestamp.desc())
            .limit(limit)
        )
        
        return list(result.scalars().all())
    
    async def add_viewership_record(
        self,
        livestream_id: int,
        viewcount: int,
        timestamp: datetime = None,
    ) -> ViewershipHistory:
        """Add a viewership record."""
        record = ViewershipHistory(
            livestream_id=livestream_id,
            viewcount=viewcount,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        
        self.session.add(record)
        await self.session.flush()
        
        return record
    
    async def cleanup_old_history(self, retention_days: int = 30) -> int:
        """Delete viewership history older than retention period.
        
        Returns:
            Number of deleted records
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        result = await self.session.execute(
            delete(ViewershipHistory).where(ViewershipHistory.timestamp < cutoff)
        )
        
        await self.session.flush()
        return result.rowcount
    
    @staticmethod
    def _extract_video_id(url_or_id: str) -> str:
        """Extract YouTube video ID from URL or return if already an ID."""
        # Check if it's already a video ID (11 characters)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id
        
        # Try to extract from various URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/live\/)([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from: {url_or_id}")
