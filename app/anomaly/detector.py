"""
Anomaly Detector - Orchestration Layer
======================================

High-level interface for running anomaly detection across multiple
livestreams. Handles data fetching, batch processing, and ranking.

This module provides:
- AnomalyDetector class for sync stateful detection
- AsyncAnomalyDetector class for async detection (FastAPI compatible)
- detect_anomalies() convenience function for one-shot detection
- Integration with SQLAlchemy session and models

Usage:
    # Sync usage
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.anomaly import AnomalyDetector, AnomalyConfig
    
    engine = create_engine("mysql+pymysql://...")
    
    with Session(engine) as session:
        detector = AnomalyDetector(session)
        rankings = detector.detect_all_live_streams()
        
        for score in rankings[:10]:
            print(f"{score.livestream_id}: {score.score:.1f} ({score.status})")
    
    # Async usage (FastAPI)
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.anomaly import AsyncAnomalyDetector
    
    async def get_rankings(session: AsyncSession):
        detector = AsyncAnomalyDetector(session)
        return await detector.detect_all_live_streams()
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.anomaly.config import AnomalyConfig
from app.anomaly.factory import AnomalyStrategyFactory
from app.anomaly.protocol import (
    AnomalyStrategy,
    AnomalyScore,
    AnomalyStatus,
    ViewershipData,
)
from app.models import Livestream, ViewershipHistory


class AnomalyDetector:
    """
    Orchestrates anomaly detection for livestreams.
    
    Handles:
    - Fetching viewership data from the database
    - Splitting data into recent/baseline windows
    - Running detection strategy
    - Ranking streams by anomaly score
    
    Attributes:
        session: SQLAlchemy database session
        config: Detection configuration
        strategy: Detection algorithm strategy
    
    Example:
        detector = AnomalyDetector(session)
        
        # Detect for all live streams
        rankings = detector.detect_all_live_streams()
        
        # Detect for specific stream
        score = detector.detect_for_stream(livestream_id=123)
        
        # Custom configuration
        config = AnomalyConfig(
            algorithm='zscore',
            recent_window_minutes=30,
        )
        detector = AnomalyDetector(session, config)
    """
    
    def __init__(
        self,
        session: Session,
        config: Optional[AnomalyConfig] = None,
        strategy: Optional[AnomalyStrategy] = None,
    ):
        """
        Initialize the anomaly detector.
        
        Args:
            session: SQLAlchemy session for database access
            config: Detection configuration (defaults used if None)
            strategy: Detection strategy (created from config if None)
        """
        self.session = session
        self.config = config or AnomalyConfig()
        self.strategy = strategy or AnomalyStrategyFactory.create(self.config)
    
    def detect_all_live_streams(
        self,
        limit: Optional[int] = None,
    ) -> List[AnomalyScore]:
        """
        Run anomaly detection for all currently live streams.
        
        Returns a ranked list of streams sorted by anomaly score
        (highest first).
        
        Args:
            limit: Optional maximum number of results
        
        Returns:
            List of AnomalyScore objects sorted by score descending
        """
        # Get all live streams
        live_streams = Livestream.get_live_streams(self.session)
        
        # Run detection for each
        scores = []
        for stream in live_streams:
            score = self.detect_for_stream(stream.id, stream.youtube_video_id)
            scores.append(score)
        
        # Sort by score descending
        scores.sort(key=lambda s: s.score, reverse=True)
        
        if limit:
            scores = scores[:limit]
        
        return scores
    
    def detect_for_stream(
        self,
        livestream_id: int,
        youtube_video_id: Optional[str] = None,
    ) -> AnomalyScore:
        """
        Run anomaly detection for a single stream.
        
        Args:
            livestream_id: Database ID of the livestream
            youtube_video_id: YouTube video ID (fetched if not provided)
        
        Returns:
            AnomalyScore with detection result
        """
        # Get YouTube ID if not provided
        if youtube_video_id is None:
            stream = self.session.get(Livestream, livestream_id)
            if stream is None:
                return AnomalyScore(
                    livestream_id=livestream_id,
                    youtube_video_id="unknown",
                    score=0.0,
                    status=AnomalyStatus.ERROR,
                    algorithm=self.strategy.name,
                    metadata={'reason': 'Stream not found'},
                )
            youtube_video_id = stream.youtube_video_id
        
        # Fetch viewership data
        now = datetime.utcnow()
        recent_start = now - timedelta(minutes=self.config.recent_window_minutes)
        baseline_start = now - timedelta(hours=self.config.baseline_hours)
        
        # Fetch all data in one query for efficiency
        all_data = self._fetch_viewership_data(
            livestream_id,
            youtube_video_id,
            baseline_start,
            now,
        )
        
        # Check for inactive stream (no recent data)
        if all_data.is_empty:
            return AnomalyScore(
                livestream_id=livestream_id,
                youtube_video_id=youtube_video_id,
                score=0.0,
                status=AnomalyStatus.INACTIVE,
                algorithm=self.strategy.name,
                metadata={'reason': 'No viewership data found'},
            )
        
        # Check if stream has recent activity
        latest_ts = all_data.latest_timestamp
        if latest_ts is None:
            inactive_cutoff = now - timedelta(minutes=self.config.inactive_threshold_minutes)
            if all_data.latest_timestamp and all_data.latest_timestamp < inactive_cutoff:
                return AnomalyScore(
                    livestream_id=livestream_id,
                    youtube_video_id=youtube_video_id,
                    score=0.0,
                    status=AnomalyStatus.INACTIVE,
                    algorithm=self.strategy.name,
                    metadata={'reason': 'No recent activity'},
                )
        
        # Split into recent and baseline windows
        recent_cutoff = np.datetime64(recent_start, 'us')
        baseline_end = np.datetime64(recent_start, 'us')  # Baseline excludes recent
        baseline_begin = np.datetime64(baseline_start, 'us')
        
        recent_data = all_data.slice_recent(recent_cutoff)
        baseline_data = all_data.slice_baseline(baseline_begin, baseline_end)
        
        # Run detection strategy
        return self.strategy.compute_score(recent_data, baseline_data)
    
    def detect_batch(
        self,
        livestream_ids: List[int],
    ) -> List[AnomalyScore]:
        """
        Run detection for a batch of streams.
        
        More efficient than calling detect_for_stream repeatedly
        as it can batch database queries.
        
        Args:
            livestream_ids: List of livestream database IDs
        
        Returns:
            List of AnomalyScores (same order as input)
        """
        scores = []
        for lid in livestream_ids:
            score = self.detect_for_stream(lid)
            scores.append(score)
        return scores
    
    def get_trending_streams(
        self,
        min_score: float = 50.0,
        limit: int = 20,
    ) -> List[AnomalyScore]:
        """
        Get streams that are currently trending.
        
        Convenience method that filters for trending status and
        minimum score threshold.
        
        Args:
            min_score: Minimum anomaly score (default 50)
            limit: Maximum results (default 20)
        
        Returns:
            List of trending streams sorted by score
        """
        all_scores = self.detect_all_live_streams()
        
        trending = [
            s for s in all_scores
            if s.status == AnomalyStatus.TRENDING and s.score >= min_score
        ]
        
        return trending[:limit]
    
    def _fetch_viewership_data(
        self,
        livestream_id: int,
        youtube_video_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> ViewershipData:
        """
        Fetch viewership history from database.
        
        Args:
            livestream_id: Stream database ID
            youtube_video_id: YouTube video ID
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            ViewershipData containing time-series data
        """
        stmt = (
            select(ViewershipHistory.timestamp, ViewershipHistory.viewcount)
            .where(
                and_(
                    ViewershipHistory.livestream_id == livestream_id,
                    ViewershipHistory.timestamp >= start_time,
                    ViewershipHistory.timestamp <= end_time,
                )
            )
            .order_by(ViewershipHistory.timestamp)
        )
        
        results = self.session.execute(stmt).fetchall()
        
        if not results:
            return ViewershipData(
                livestream_id=livestream_id,
                youtube_video_id=youtube_video_id,
                timestamps=np.array([], dtype='datetime64[us]'),
                viewcounts=np.array([], dtype=np.int64),
            )
        
        timestamps = np.array(
            [r[0] for r in results],
            dtype='datetime64[us]'
        )
        viewcounts = np.array(
            [r[1] for r in results],
            dtype=np.int64
        )
        
        return ViewershipData(
            livestream_id=livestream_id,
            youtube_video_id=youtube_video_id,
            timestamps=timestamps,
            viewcounts=viewcounts,
        )


def detect_anomalies(
    session: Session,
    strategy: Optional[AnomalyStrategy] = None,
    config: Optional[AnomalyConfig] = None,
    live_only: bool = True,
) -> List[AnomalyScore]:
    """
    Convenience function for one-shot anomaly detection.
    
    Creates a detector and runs detection for all (live) streams.
    Use AnomalyDetector class directly for more control.
    
    Args:
        session: SQLAlchemy database session
        strategy: Detection strategy (created from config if None)
        config: Detection configuration (defaults if None)
        live_only: If True, only process live streams (default)
    
    Returns:
        List of AnomalyScores ranked by score (highest first)
    
    Example:
        with Session(engine) as session:
            # Quick detection with defaults
            rankings = detect_anomalies(session)
            
            # With custom config
            config = AnomalyConfig(algorithm='zscore')
            rankings = detect_anomalies(session, config=config)
    """
    config = config or AnomalyConfig()
    detector = AnomalyDetector(session, config, strategy)
    
    if live_only:
        return detector.detect_all_live_streams()
    
    # For non-live: get all streams (implement if needed)
    return detector.detect_all_live_streams()


class AsyncAnomalyDetector:
    """
    Async version of AnomalyDetector for use with FastAPI and AsyncSession.
    
    Provides the same detection capabilities as AnomalyDetector but with
    async/await support for non-blocking database operations.
    
    Attributes:
        session: Async SQLAlchemy database session
        config: Detection configuration
        strategy: Detection algorithm strategy
    
    Example:
        async def get_rankings(session: AsyncSession):
            detector = AsyncAnomalyDetector(session)
            scores = await detector.detect_all_live_streams()
            return scores[:10]
    """
    
    def __init__(
        self,
        session: AsyncSession,
        config: Optional[AnomalyConfig] = None,
        strategy: Optional[AnomalyStrategy] = None,
    ):
        """
        Initialize the async anomaly detector.
        
        Args:
            session: AsyncSession for async database access
            config: Detection configuration (defaults used if None)
            strategy: Detection strategy (created from config if None)
        """
        self.session = session
        self.config = config or AnomalyConfig()
        self.strategy = strategy or AnomalyStrategyFactory.create(self.config)

    def validate_data(
        self,
        recent_data: ViewershipData,
        baseline_data: ViewershipData,
        min_recent: int,
        min_baseline: int,
    ) -> Optional[AnomalyStatus]:
        """
        Validate input data meets minimum requirements and if the stream is inactive.
        
        Returns:
            AnomalyStatus if validation fails, None if valid
        """
        if recent_data.sample_count < min_recent:
            #print(f"Validation failed: recent sample count {recent_data.sample_count} < min {min_recent}")
            return AnomalyStatus.INSUFFICIENT_DATA
        if baseline_data.sample_count < min_baseline:
            #print(f"Validation failed: baseline sample count {baseline_data.sample_count} < min {min_baseline}")
            return AnomalyStatus.INSUFFICIENT_DATA
        
        if recent_data.is_empty:
            return AnomalyStatus.INACTIVE
            
        recent_median = np.median(recent_data.viewcounts)
        recent_max = np.max(recent_data.viewcounts)
        
        # Check for zero viewership
        if recent_median == 0 and recent_max == 0:
            return AnomalyStatus.INACTIVE
        
        # Check minimum viewcount threshold
        if recent_max < self.config.min_viewcount:
            return AnomalyStatus.INACTIVE
        
        # Check for dramatic drop from baseline
        if not baseline_data.is_empty:
            baseline_median = np.median(baseline_data.viewcounts)
            if baseline_median > 100 and recent_max < baseline_median * 0.01:
                return AnomalyStatus.INACTIVE
        
        return None
    
    async def detect_all_live_streams(
        self,
        limit: Optional[int] = None,
    ) -> List[AnomalyScore]:
        """
        Run anomaly detection for all currently live streams.
        
        Returns a ranked list of streams sorted by anomaly score
        (highest first).
        
        Args:
            limit: Optional maximum number of results
        
        Returns:
            List of AnomalyScore objects sorted by score descending
        """
        #print(f"Running anomaly detection with config: {self.config}")

        # Get all live streams
        result = await self.session.execute(
            select(Livestream).where(Livestream.is_live == True)
        )
        live_streams = result.scalars().all()
        
        # Run detection for each
        scores = []
        for stream in live_streams:
            score = await self.detect_for_stream(stream)
            scores.append(score)
        
        # Sort by score descending
        scores.sort(key=lambda s: s.score, reverse=True)
        
        if limit:
            scores = scores[:limit]
        
        return scores
    
    async def detect_for_stream(
        self,
        livestream: Livestream,
    ) -> AnomalyScore:
        """
        Run anomaly detection for a single stream.
        
        Args:
            livestream: Livestream model instance
        
        Returns:
            AnomalyScore with detection result
        """
        now = datetime.now(timezone.utc)
        recent_start = now - timedelta(minutes=self.config.recent_window_minutes)
        baseline_start = now - timedelta(hours=self.config.baseline_hours)
        
        # Fetch all viewership data
        all_data = await self._fetch_viewership_data(
            livestream=livestream,
            start_time=baseline_start,
            end_time=now,
        )
        
        # Check for inactive stream (no data)
        if all_data.is_empty:
            #print(f"Stream {livestream.id} has no viewership data. Marking as INACTIVE.")
            return AnomalyScore(
                livestream_id=livestream.id,
                youtube_video_id=livestream.youtube_video_id,
                name=livestream.name,
                channel=livestream.channel,
                score=self.config.score_min,
                status=AnomalyStatus.INACTIVE,
                algorithm=self.strategy.name,
                metadata={'reason': 'No viewership data found'},
            )
        
        # Split into recent and baseline windows
        recent_cutoff = np.datetime64(recent_start, 'us')
        baseline_end = np.datetime64(recent_start, 'us')
        baseline_begin = np.datetime64(baseline_start, 'us')
        
        recent_data = all_data.slice_recent(recent_cutoff)
        baseline_data = all_data.slice_baseline(baseline_begin, baseline_end)

        # Validate data meets minimum requirements
        validation_status = self.validate_data(
            recent_data,
            baseline_data,
            self.config.min_recent_samples,
            self.config.min_baseline_samples,
        )

        if validation_status is not None:
            #print(f"Stream {livestream.id} failed validation: {validation_status}")
            return AnomalyScore(
                livestream_id=livestream.id,
                youtube_video_id=livestream.youtube_video_id,
                name=livestream.name,
                channel=livestream.channel,
                score=self.config.score_min,
                status=validation_status,
                current_viewcount=recent_data.latest_viewcount,
                algorithm=self.strategy.name,
                metadata={'reason': str(validation_status)},
            )
        
        # Run detection strategy
        score = self.strategy.compute_score(recent_data, baseline_data)
        
        # Enrich with stream metadata
        score.name = livestream.name
        score.channel = livestream.channel
        score.last_updated = all_data.latest_timestamp
        score.current_viewcount = all_data.latest_viewcount
        
        return score
    
    async def _fetch_viewership_data(
        self,
        livestream: Livestream,
        start_time: datetime,
        end_time: datetime,
    ) -> ViewershipData:
        """
        Fetch viewership history from database asynchronously.
        
        Args:
            livestream: Livestream model instance
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            ViewershipData containing time-series data
        """
        stmt = (
            select(ViewershipHistory.timestamp, ViewershipHistory.viewcount)
            .where(
                and_(
                    ViewershipHistory.livestream_id == livestream.id,
                    ViewershipHistory.timestamp >= start_time,
                    ViewershipHistory.timestamp <= end_time,
                )
            )
            .order_by(ViewershipHistory.timestamp)
        )
        
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        
        if not rows:
            return ViewershipData(
                livestream_id=livestream.id,
                youtube_video_id=livestream.youtube_video_id,
                name=livestream.name,
                channel=livestream.channel,
                timestamps=np.array([], dtype='datetime64[us]'),
                viewcounts=np.array([], dtype=np.int64),
            )
        
        timestamps = np.array(
            [r[0] for r in rows],
            dtype='datetime64[us]'
        )
        viewcounts = np.array(
            [r[1] for r in rows],
            dtype=np.int64
        )
        
        return ViewershipData(
            livestream_id=livestream.id,
            youtube_video_id=livestream.youtube_video_id,
            name=livestream.name,
            channel=livestream.channel,
            timestamps=timestamps,
            viewcounts=viewcounts,
        )


async def detect_anomalies_async(
    session: AsyncSession,
    strategy: Optional[AnomalyStrategy] = None,
    config: Optional[AnomalyConfig] = None,
    limit: Optional[int] = None,
) -> List[AnomalyScore]:
    """
    Async convenience function for one-shot anomaly detection.
    
    Creates an async detector and runs detection for all live streams.
    
    Args:
        session: AsyncSession for async database access
        strategy: Detection strategy (created from config if None)
        config: Detection configuration (defaults if None)
        limit: Maximum number of results to return
    
    Returns:
        List of AnomalyScores ranked by score (highest first)
    
    Example:
        async with AsyncSession(engine) as session:
            rankings = await detect_anomalies_async(session, limit=10)
    """
    config = config or AnomalyConfig()
    detector = AsyncAnomalyDetector(session, config, strategy)
    return await detector.detect_all_live_streams(limit=limit)
