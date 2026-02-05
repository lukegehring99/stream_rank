"""High-level anomaly detector with database integration."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Livestream, ViewershipHistory
from .config import AnomalyConfig
from .interface import AnomalyScore, AnomalyStrategy, ViewershipData
from .factory import get_anomaly_strategy


class AnomalyDetector:
    """High-level anomaly detection orchestrator.
    
    Coordinates between database queries and anomaly detection strategies
    to produce ranked scores for all livestreams.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        config: AnomalyConfig = None,
        strategy: AnomalyStrategy = None,
    ):
        self.session = session
        self.config = config or AnomalyConfig()
        self.strategy = strategy or get_anomaly_strategy(self.config)
    
    async def detect_all_live_streams(
        self,
        limit: int = 100,
    ) -> List[AnomalyScore]:
        """Detect anomalies for all live streams.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of AnomalyScore sorted by score descending
        """
        # Get all live streams
        result = await self.session.execute(
            select(Livestream).where(Livestream.is_live == True)
        )
        livestreams = result.scalars().all()
        
        scores = []
        for livestream in livestreams:
            score = await self.detect_for_stream(livestream)
            scores.append(score)
        
        # Sort by score descending and limit
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:limit]
    
    async def detect_for_stream(
        self,
        livestream: Livestream,
    ) -> AnomalyScore:
        """Detect anomaly for a single livestream.
        
        Args:
            livestream: Livestream model instance
            
        Returns:
            AnomalyScore for the stream
        """
        # Calculate time boundaries
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(minutes=self.config.recent_window_minutes)
        baseline_cutoff = now - timedelta(hours=self.config.baseline_hours)
        
        # Fetch viewership data
        viewership_data = await self._fetch_viewership_data(
            livestream_id=livestream.id,
            since=baseline_cutoff,
        )
        
        # Split into recent and baseline
        recent_data = []
        baseline_data = []
        
        for ts, vc in zip(viewership_data.timestamps, viewership_data.viewcounts):
            if ts >= recent_cutoff:
                recent_data.append(vc)
            baseline_data.append(vc)  # Baseline includes all data
        
        # Calculate score using strategy
        score, debug_info = self.strategy.calculate_score(recent_data, baseline_data)
        
        return AnomalyScore(
            livestream_id=livestream.id,
            youtube_video_id=livestream.youtube_video_id,
            name=livestream.name,
            channel=livestream.channel,
            score=score,
            current_viewers=viewership_data.latest_viewcount,
            last_updated=viewership_data.latest_timestamp,
            baseline_mean=debug_info.get("baseline_mean") or debug_info.get("baseline_value"),
            recent_mean=debug_info.get("recent_mean") or debug_info.get("recent_value"),
            raw_score=debug_info.get("raw_score"),
        )
    
    async def _fetch_viewership_data(
        self,
        livestream_id: int,
        since: datetime,
    ) -> ViewershipData:
        """Fetch viewership history from database."""
        result = await self.session.execute(
            select(ViewershipHistory)
            .where(
                and_(
                    ViewershipHistory.livestream_id == livestream_id,
                    ViewershipHistory.timestamp >= since,
                )
            )
            .order_by(ViewershipHistory.timestamp)
        )
        records = result.scalars().all()
        
        # Get livestream info
        ls_result = await self.session.execute(
            select(Livestream).where(Livestream.id == livestream_id)
        )
        livestream = ls_result.scalar_one_or_none()
        
        return ViewershipData(
            livestream_id=livestream_id,
            youtube_video_id=livestream.youtube_video_id if livestream else "",
            name=livestream.name if livestream else "",
            channel=livestream.channel if livestream else "",
            timestamps=[r.timestamp for r in records],
            viewcounts=[r.viewcount for r in records],
        )
