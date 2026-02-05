"""Public API endpoints."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.anomaly import AnomalyConfig, AnomalyDetector
from app.config import get_settings
from app.db import get_db_session
from app.schemas import HealthResponse, LivestreamListResponse, LivestreamRanked
from app.services import CacheService

router = APIRouter(tags=["Public"])


def get_cache_service() -> CacheService:
    """Dependency to get cache service."""
    settings = get_settings()
    return CacheService(
        ttl_seconds=settings.cache_ttl_minutes * 60,
        max_items=settings.cache_max_items,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/livestreams", response_model=LivestreamListResponse)
async def get_trending_livestreams(
    count: int = Query(default=10, ge=1, le=100, description="Number of streams to return"),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
) -> LivestreamListResponse:
    """Get trending livestreams ranked by anomaly score.
    
    Returns cached results when available. Cache refreshes every 5 minutes (configurable).
    """
    settings = get_settings()
    
    # Try to get from cache
    cached = cache.rankings.get(count)
    if cached is not None:
        items, cached_at, remaining_ttl = cached
        return LivestreamListResponse(
            items=items,
            total=len(items),
            cached_at=cached_at,
            cache_ttl_seconds=remaining_ttl,
        )
    
    # Cache miss - compute rankings
    config = AnomalyConfig(
        algorithm=settings.anomaly_algorithm,
        recent_window_minutes=settings.anomaly_recent_window_minutes,
        baseline_hours=settings.anomaly_baseline_hours,
    )
    
    detector = AnomalyDetector(session=session, config=config)
    scores = await detector.detect_all_live_streams(limit=settings.cache_max_items)
    
    # Convert to response models with ranks
    ranked_items = [
        LivestreamRanked(
            id=score.livestream_id,
            youtube_video_id=score.youtube_video_id,
            name=score.name,
            channel=score.channel,
            description=None,  # Excluded for performance
            url=f"https://www.youtube.com/watch?v={score.youtube_video_id}",
            is_live=True,
            rank=idx + 1,
            trend_score=score.score,
            current_viewers=score.current_viewers,
            last_updated=score.last_updated,
        )
        for idx, score in enumerate(scores)
    ]
    
    # Update cache
    cache.rankings.set(ranked_items)
    
    # Return requested count
    now = datetime.now(timezone.utc)
    return LivestreamListResponse(
        items=ranked_items[:count],
        total=len(ranked_items[:count]),
        cached_at=now,
        cache_ttl_seconds=settings.cache_ttl_minutes * 60,
    )
