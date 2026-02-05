"""
Viewership Schemas
==================

Request and response schemas for viewership history endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field


class DownsampleInterval(str, Enum):
    """Downsampling interval options for viewership history."""
    
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    TEN_MINUTES = "10m"
    ONE_HOUR = "1hr"


# Mapping from enum to seconds for SQL aggregation
DOWNSAMPLE_SECONDS = {
    DownsampleInterval.ONE_MINUTE: 60,       # 1 * 60
    DownsampleInterval.FIVE_MINUTES: 300,    # 5 * 60
    DownsampleInterval.TEN_MINUTES: 600,     # 10 * 60
    DownsampleInterval.ONE_HOUR: 3600,       # 60 * 60
}


class ViewershipHistoryResponse(BaseModel):
    """Response schema for a single viewership history entry."""
    
    id: int = Field(..., description="Unique identifier")
    livestream_id: int = Field(..., description="Associated livestream ID")
    timestamp: datetime = Field(..., description="Measurement timestamp (UTC)")
    viewcount: int = Field(..., description="Concurrent viewer count")
    
    model_config = {"from_attributes": True}


class DownsampledViewershipResponse(BaseModel):
    """Response schema for a downsampled viewership history entry."""
    
    id: str = Field(..., description="Binned identifier (original_id + interval suffix)")
    livestream_id: int = Field(..., description="Associated livestream ID")
    timestamp: datetime = Field(..., description="Bin start timestamp (UTC)")
    viewcount: int = Field(..., description="Average viewer count for the bin")


class ViewershipHistoryListResponse(BaseModel):
    """Response schema for viewership history list."""
    
    items: list[Union[ViewershipHistoryResponse, DownsampledViewershipResponse]] = Field(
        ..., 
        description="List of viewership history entries (raw or downsampled)"
    )
    total: int = Field(..., description="Total number of entries")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    total_pages: int = Field(1, description="Total number of pages")
    livestream_id: str = Field(..., description="Livestream public ID (UUID)")
    start_time: Optional[datetime] = Field(
        None, 
        description="Query start time filter"
    )
    end_time: Optional[datetime] = Field(
        None, 
        description="Query end time filter"
    )
    downsample: Optional[DownsampleInterval] = Field(
        None,
        description="Downsample interval applied to the data"
    )
