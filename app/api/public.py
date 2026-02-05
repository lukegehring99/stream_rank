"""
Public API Routes
=================

Unauthenticated endpoints for public consumption.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.db import get_async_session
from app.schemas import HealthResponse, TrendingLivestreamsResponse
from app.services import LivestreamService, get_cache_service, CacheKeys


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
