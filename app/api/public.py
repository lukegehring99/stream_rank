"""
Public API Routes
=================

Unauthenticated endpoints for public consumption.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.db import get_async_session
from app.schemas import (
    HealthResponse,
    TrendingLivestreamsResponse,
    DownsampleInterval,
    PublicViewershipDataPoint,
    PublicViewershipResponse,
)
from app.services import LivestreamService, get_cache_service, CacheKeys


# Cache TTL for public viewership endpoint (10 minutes)
PUBLIC_VIEWERSHIP_CACHE_TTL = 600


router = APIRouter(tags=["Public"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API and its dependencies.",
)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the current health status of the API, including:
    - Overall status
    - Database connectivity
    - API version
    """
    # Test database connectivity
    db_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.app_version,
        database=db_status,
    )


@router.get(
    "/livestreams",
    response_model=TrendingLivestreamsResponse,
    summary="Get Trending Livestreams",
    description="Get a ranked list of trending YouTube livestreams.",
)
async def get_trending_livestreams(
    count: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Number of livestreams to return (1-100)",
        ),
    ] = 10,
    session: Annotated[AsyncSession, Depends(get_async_session)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> TrendingLivestreamsResponse:
    """
    Get trending livestreams.
    
    Returns a ranked list of currently live YouTube streams,
    ordered by current viewer count (descending).
    
    Results are cached for performance with a configurable TTL.
    
    Args:
        count: Number of items to return (default: 10, max: 100)
    
    Returns:
        Ranked list of trending livestreams with viewer counts
    """
    # Clamp count to configured maximum
    max_count = min(count, settings.max_livestreams_count)
    
    # Get cached timestamp if available
    cache_service = get_cache_service()
    cached_item = cache_service.get(CacheKeys.TRENDING_LIVESTREAMS)
    cached_at = cached_item.cached_at if cached_item else None
    
    # Fetch trending data (service handles caching internally)
    service = LivestreamService(session)
    items = await service.get_trending(count=max_count)
    
    # Update cached_at if we just populated the cache
    if cached_at is None:
        cached_item = cache_service.get(CacheKeys.TRENDING_LIVESTREAMS)
        cached_at = cached_item.cached_at if cached_item else None
    
    return TrendingLivestreamsResponse(
        items=items,
        count=len(items),
        cached_at=cached_at,
    )


@router.get(
    "/livestreams/experimental",
    response_model=TrendingLivestreamsResponse,
    summary="Get Experimental Trending Livestreams",
    description="Get trending livestreams using experimental anomaly detection settings.",
)
async def get_experimental_trending_livestreams(
    count: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Number of livestreams to return (1-100)",
        ),
    ] = 10,
    session: Annotated[AsyncSession, Depends(get_async_session)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> TrendingLivestreamsResponse:
    """
    Get trending livestreams using experimental settings.
    
    This endpoint bypasses the cache and uses anomaly detection
    configuration stored in the database. Use this to test
    different algorithm configurations before applying them.
    
    Args:
        count: Number of items to return (default: 10, max: 100)
    
    Returns:
        Ranked list of trending livestreams with viewer counts
        (not cached, uses experimental config)
    """
    # Clamp count to configured maximum
    max_count = min(count, settings.max_livestreams_count)
    
    # Fetch trending data with experimental flag (bypasses cache, uses DB config)
    service = LivestreamService(session)
    items = await service.get_trending(count=max_count, experimental=True)
    
    return TrendingLivestreamsResponse(
        items=items,
        count=len(items),
        cached_at=None,  # Experimental mode doesn't use cache
    )


@router.get(
    "/streams/{youtube_id}/viewership",
    response_model=PublicViewershipResponse,
    summary="Get Viewership History",
    description="Get viewership history for a specific YouTube stream.",
)
async def get_stream_viewership(
    youtube_id: Annotated[
        str,
        Path(
            description="YouTube video ID",
            min_length=11,
            max_length=11,
        ),
    ],
    hours: Annotated[
        int,
        Query(
            ge=1,
            le=168,
            description="Number of hours of history to return (1-168)",
        ),
    ] = 24,
    session: Annotated[AsyncSession, Depends(get_async_session)] = None,
) -> PublicViewershipResponse:
    """
    Get viewership history for a specific stream.
    
    Returns a time series of viewer counts for the specified YouTube stream,
    downsampled to 10-minute intervals for efficient transfer.
    
    Results are cached for 10 minutes.
    
    Args:
        youtube_id: YouTube video ID (11 characters)
        hours: Hours of history to return (default: 24, max: 168)
    
    Returns:
        Viewership history with data points
    
    Raises:
        404: Stream not found
    """
    # Check cache first
    cache_service = get_cache_service()
    cache_key = CacheKeys.public_viewership(youtube_id, hours)
    cached_item = cache_service.get(cache_key)
    
    if cached_item and not cached_item.is_expired:
        return cached_item.data
    
    # Look up the stream
    service = LivestreamService(session)
    livestream = await service.get_by_youtube_id(youtube_id)
    
    if not livestream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Calculate time range
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    # Get viewership history with 10-minute downsampling
    history, _ = await service.get_viewership_history(
        livestream_id=livestream.id,
        start_time=start_time,
        end_time=end_time,
        skip=0,
        limit=1000,  # Max data points
        downsample=DownsampleInterval.TEN_MINUTES,
    )
    
    # Convert to public response format
    data_points = [
        PublicViewershipDataPoint(
            timestamp=entry.timestamp,
            viewers=entry.viewcount,
        )
        for entry in sorted(history, key=lambda x: x.timestamp)
    ]
    
    response = PublicViewershipResponse(
        video_id=youtube_id,
        history=data_points,
        period_hours=hours,
    )
    
    # Cache the response
    cache_service.set(cache_key, response, ttl_seconds=PUBLIC_VIEWERSHIP_CACHE_TTL)
    
    return response
