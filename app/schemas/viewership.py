"""
Viewership Schemas
==================

Request and response schemas for viewership history endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ViewershipHistoryResponse(BaseModel):
    """Response schema for a single viewership history entry."""
    
    id: int = Field(..., description="Unique identifier")
    livestream_id: int = Field(..., description="Associated livestream ID")
    timestamp: datetime = Field(..., description="Measurement timestamp (UTC)")
    viewcount: int = Field(..., description="Concurrent viewer count")
    
    model_config = {"from_attributes": True}


class ViewershipHistoryListResponse(BaseModel):
    """Response schema for viewership history list."""
    
    items: list[ViewershipHistoryResponse] = Field(
        ..., 
        description="List of viewership history entries"
    )
    total: int = Field(..., description="Total number of entries")
    livestream_id: str = Field(..., description="Livestream public ID (UUID)")
    start_time: Optional[datetime] = Field(
        None, 
        description="Query start time filter"
    )
    end_time: Optional[datetime] = Field(
        None, 
        description="Query end time filter"
    )
