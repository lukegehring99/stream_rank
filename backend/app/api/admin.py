"""Admin API endpoints (JWT protected)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_auth
from app.db import get_db_session
from app.schemas import (
    LivestreamCreate,
    LivestreamResponse,
    LivestreamUpdate,
    PaginatedResponse,
    ViewershipHistoryResponse,
    ViewershipRecord,
)
from app.services import LivestreamService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_auth)],
)


@router.get("/livestreams", response_model=PaginatedResponse[LivestreamResponse])
async def list_livestreams(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_live: Optional[bool] = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[LivestreamResponse]:
    """List all livestreams with pagination."""
    service = LivestreamService(session)
    
    skip = (page - 1) * page_size
    livestreams, total = await service.get_all(
        skip=skip,
        limit=page_size,
        is_live=is_live,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=[LivestreamResponse.model_validate(ls) for ls in livestreams],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/livestreams", response_model=LivestreamResponse, status_code=status.HTTP_201_CREATED)
async def create_livestream(
    data: LivestreamCreate,
    session: AsyncSession = Depends(get_db_session),
) -> LivestreamResponse:
    """Create a new livestream."""
    service = LivestreamService(session)
    
    # Check for duplicate
    try:
        video_id = service._extract_video_id(data.youtube_url_or_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    existing = await service.get_by_youtube_id(video_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Livestream with YouTube ID '{video_id}' already exists",
        )
    
    livestream = await service.create(data)
    return LivestreamResponse.model_validate(livestream)


@router.get("/livestreams/{livestream_id}", response_model=LivestreamResponse)
async def get_livestream(
    livestream_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> LivestreamResponse:
    """Get a single livestream by ID."""
    service = LivestreamService(session)
    livestream = await service.get_by_id(livestream_id)
    
    if not livestream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )
    
    return LivestreamResponse.model_validate(livestream)


@router.put("/livestreams/{livestream_id}", response_model=LivestreamResponse)
async def update_livestream(
    livestream_id: int,
    data: LivestreamUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> LivestreamResponse:
    """Update a livestream."""
    service = LivestreamService(session)
    livestream = await service.update(livestream_id, data)
    
    if not livestream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )
    
    return LivestreamResponse.model_validate(livestream)


@router.delete("/livestreams/{livestream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_livestream(
    livestream_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a livestream and its history."""
    service = LivestreamService(session)
    deleted = await service.delete(livestream_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )


@router.get("/livestreams/{livestream_id}/history", response_model=ViewershipHistoryResponse)
async def get_viewership_history(
    livestream_id: int,
    hours: int = Query(default=24, ge=1, le=720),
    session: AsyncSession = Depends(get_db_session),
) -> ViewershipHistoryResponse:
    """Get viewership history for a livestream."""
    service = LivestreamService(session)
    
    # Verify livestream exists
    livestream = await service.get_by_id(livestream_id)
    if not livestream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Livestream with ID {livestream_id} not found",
        )
    
    records = await service.get_viewership_history(livestream_id, hours=hours)
    
    return ViewershipHistoryResponse(
        livestream_id=livestream_id,
        livestream_name=livestream.name,
        records=[ViewershipRecord.model_validate(r) for r in records],
        total_records=len(records),
    )
