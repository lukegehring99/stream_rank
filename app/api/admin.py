"""
Admin API Routes
================

JWT-protected endpoints for administrative operations.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.db import get_async_session
from app.schemas import (
    LivestreamCreate,
    LivestreamUpdate,
    LivestreamResponse,
    LivestreamListResponse,
    ViewershipHistoryListResponse,
    DashboardStats,
    DownsampleInterval,
    AnomalyConfigEntry,
    AnomalyConfigListResponse,
    AnomalyConfigUpdateRequest,
    AnomalyConfigUpdateResponse,
)
from app.services import LivestreamService, AnomalyConfigService


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
    },
)


# ============================================================================
# Dashboard Stats Endpoint
# ============================================================================

@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get Dashboard Statistics",
    description="Get aggregated statistics for the admin dashboard.",
)
async def get_dashboard_stats(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DashboardStats:
    """
    Get dashboard statistics.
    
    Requires admin authentication.
    
    Returns:
        Dashboard statistics including stream counts and viewer totals
    """
    service = LivestreamService(session)
    stats = await service.get_dashboard_stats()
    return DashboardStats(**stats)


# ============================================================================
# Livestream CRUD Endpoints
# ============================================================================

@router.get(
    "/livestreams",
    response_model=LivestreamListResponse,
    summary="List All Livestreams",
    description="Get a paginated list of all livestreams (admin only).",
)
async def list_livestreams(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
    search: Annotated[Optional[str], Query(description="Search term for name or channel")] = None,
    is_live: Annotated[Optional[bool], Query(description="Filter by live status")] = None,
    sort_by: Annotated[Optional[str], Query(description="Field to sort by")] = None,
    sort_order: Annotated[Optional[str], Query(description="Sort order (asc or desc)")] = None,
) -> LivestreamListResponse:
    """
    List all livestreams with pagination.
    
    Requires admin authentication.
    
    Args:
        page: Page number (1-based)
        page_size: Maximum items per page (1-100)
        search: Optional search term
        is_live: Optional filter by live status
    
    Returns:
        Paginated list of livestreams with total count
    """
    service = LivestreamService(session)
    skip = (page - 1) * page_size
    livestreams, total = await service.get_all(
        skip=skip, 
        limit=page_size, 
        search=search,
        is_live=is_live,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_pages = (total + page_size - 1) // page_size
    
    # Fetch current viewers for all livestreams in this batch
    livestream_ids = [ls.id for ls in livestreams]
    current_viewers_map = await service.get_current_viewers_map(livestream_ids)
    
    # Build response items with current_viewers
    items = []
    for ls in livestreams:
        response = LivestreamResponse.model_validate(ls)
        response.current_viewers = current_viewers_map.get(ls.id)
        items.append(response)
    
    return LivestreamListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/livestreams",
    response_model=LivestreamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Livestream",
    description="Create a new livestream by YouTube video ID or URL.",
)
async def create_livestream(
    current_user: CurrentUser,
    data: LivestreamCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LivestreamResponse:
    """
    Create a new livestream.
    
    Accepts either a YouTube video ID or full URL. The video ID will be
    extracted from the URL if provided.
    
    Requires admin authentication.
    
    Args:
        data: Livestream creation data
    
    Returns:
        Created livestream details
    
    Raises:
        HTTPException: 400 if video ID already exists
    """
    service = LivestreamService(session)
    
    try:
        livestream = await service.create(data)
        return LivestreamResponse.model_validate(livestream)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/livestreams/{livestream_id}",
    response_model=LivestreamResponse,
    summary="Get Livestream",
    description="Get details of a specific livestream.",
)
async def get_livestream(
    livestream_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LivestreamResponse:
    """
    Get a single livestream by ID.
    
    Requires admin authentication.
    
    Args:
        livestream_id: Livestream public ID (UUID)
    
    Returns:
        Livestream details
    
    Raises:
        HTTPException: 404 if not found
    """
    service = LivestreamService(session)
    livestream = await service.get_by_public_id(livestream_id)
    
    if not livestream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )
    
    # Fetch current viewers
    current_viewers = await service.get_current_viewers(livestream.id)
    
    response = LivestreamResponse.model_validate(livestream)
    response.current_viewers = current_viewers
    return response


@router.put(
    "/livestreams/{livestream_id}",
    response_model=LivestreamResponse,
    summary="Update Livestream",
    description="Update metadata for an existing livestream.",
)
async def update_livestream(
    livestream_id: str,
    data: LivestreamUpdate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LivestreamResponse:
    """
    Update a livestream's metadata.
    
    Only fields provided in the request body will be updated.
    Requires admin authentication.
    
    Args:
        livestream_id: Livestream public ID (UUID)
        data: Fields to update
    
    Returns:
        Updated livestream details
    
    Raises:
        HTTPException: 404 if not found
    """
    service = LivestreamService(session)
    livestream = await service.update_by_public_id(livestream_id, data)
    
    if not livestream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )
    
    return LivestreamResponse.model_validate(livestream)


@router.delete(
    "/livestreams/{livestream_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Livestream",
    description="Delete a livestream and all associated data.",
)
async def delete_livestream(
    livestream_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    """
    Delete a livestream.
    
    This will also delete all associated viewership history.
    Requires admin authentication.
    
    Args:
        livestream_id: Livestream public ID (UUID)
    
    Raises:
        HTTPException: 404 if not found
    """
    service = LivestreamService(session)
    deleted = await service.delete_by_public_id(livestream_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )


# ============================================================================
# Viewership History Endpoints
# ============================================================================

@router.get(
    "/livestreams/{livestream_id}/history",
    response_model=ViewershipHistoryListResponse,
    summary="Get Viewership History",
    description="Get viewership history for a specific livestream. Supports optional downsampling for large time ranges.",
)
async def get_viewership_history(
    livestream_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=3000, description="Items per page")] = 50,
    start_time: Annotated[
        Optional[datetime],
        Query(description="Start of time range (ISO 8601 format)"),
    ] = None,
    end_time: Annotated[
        Optional[datetime],
        Query(description="End of time range (ISO 8601 format)"),
    ] = None,
    downsample: Annotated[
        Optional[DownsampleInterval],
        Query(description="Downsample interval: 5m, 10m, or 1hr. Returns averaged data per time bin."),
    ] = None,
) -> ViewershipHistoryListResponse:
    """
    Get viewership history for a livestream.
    
    Returns paginated time-series data of viewer counts. Optionally filter
    by time range. Returns all history if no time range specified.
    
    When downsample is specified, data is aggregated into time bins and
    the average viewer count is returned. This is useful for viewing
    long time ranges without overwhelming the UI with raw data points.
    
    Requires admin authentication.
    
    Args:
        livestream_id: Livestream public ID (UUID)
        page: Page number (1-based)
        page_size: Items per page (1-1000)
        start_time: Optional start of time range
        end_time: Optional end of time range
        downsample: Optional downsampling interval (5m, 10m, 1hr)
    
    Returns:
        Paginated list of viewership history records
    
    Raises:
        HTTPException: 404 if livestream not found
    """
    service = LivestreamService(session)
    
    # Verify livestream exists
    livestream = await service.get_by_public_id(livestream_id)
    if not livestream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )
    
    skip = (page - 1) * page_size
    history, total = await service.get_viewership_history(
        livestream_id=livestream.id,  # Use internal ID for DB query
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=page_size,
        downsample=downsample,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return ViewershipHistoryListResponse(
        items=history,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        livestream_id=livestream_id,  # Return public ID
        start_time=start_time,
        end_time=end_time,
        downsample=downsample,
    )


# ============================================================================
# Anomaly Config Endpoints
# ============================================================================

@router.get(
    "/anomaly-config",
    response_model=AnomalyConfigListResponse,
    summary="Get Anomaly Detection Configuration",
    description="Get all anomaly detection configuration parameters.",
)
async def get_anomaly_config(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AnomalyConfigListResponse:
    """
    Get all anomaly detection configuration entries.
    
    Returns entries for all valid configuration keys, including:
    - algorithm: Detection algorithm ('quantile' or 'zscore')
    - Time window settings
    - Algorithm-specific parameters
    
    Requires admin authentication.
    
    Returns:
        List of configuration entries with current values
    """
    service = AnomalyConfigService(session)
    entries = await service.get_all()
    
    return AnomalyConfigListResponse(
        items=[AnomalyConfigEntry(**entry) for entry in entries]
    )


@router.put(
    "/anomaly-config",
    response_model=AnomalyConfigUpdateResponse,
    summary="Update Anomaly Detection Configuration",
    description="Update a single anomaly detection configuration parameter.",
)
async def update_anomaly_config(
    current_user: CurrentUser,
    data: AnomalyConfigUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AnomalyConfigUpdateResponse:
    """
    Update an anomaly detection configuration value.
    
    The key must be a valid configuration parameter. The value will be
    validated and parsed according to the parameter's expected type.
    
    Requires admin authentication.
    
    Args:
        data: Configuration update request with key and value
    
    Returns:
        Updated configuration entry
    
    Raises:
        HTTPException: 400 if key is invalid or value cannot be parsed
    """
    service = AnomalyConfigService(session)
    
    try:
        result = await service.set_value(data.key, data.value)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration key: {data.key}",
            )
        
        return AnomalyConfigUpdateResponse(
            success=True,
            entry=AnomalyConfigEntry(**result),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/anomaly-config/{key:path}",
    response_model=AnomalyConfigUpdateResponse,
    summary="Reset Anomaly Config to Default",
    description="Reset a configuration parameter to its default value.",
)
async def reset_anomaly_config(
    key: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AnomalyConfigUpdateResponse:
    """
    Reset a configuration value to its default.
    
    Removes the custom value from the database, causing the default
    to be used on subsequent reads.
    
    Requires admin authentication.
    
    Args:
        key: Configuration key to reset
    
    Returns:
        Default configuration entry
    
    Raises:
        HTTPException: 400 if key is invalid
    """
    service = AnomalyConfigService(session)
    result = await service.reset_to_default(key)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration key: {key}",
        )
    
    return AnomalyConfigUpdateResponse(
        success=True,
        entry=AnomalyConfigEntry(**result),
    )
