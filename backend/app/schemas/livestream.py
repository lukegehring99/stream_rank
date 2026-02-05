"""Livestream schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class LivestreamBase(BaseModel):
    """Base livestream schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    channel: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class LivestreamCreate(LivestreamBase):
    """Schema for creating a livestream."""
    
    youtube_url_or_id: str = Field(
        ...,
        description="YouTube video URL or video ID",
        min_length=1,
    )
    
    @field_validator("youtube_url_or_id")
    @classmethod
    def validate_youtube_input(cls, v: str) -> str:
        """Validate YouTube URL or ID format."""
        import re
        
        # Check if it's a valid video ID (11 chars)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', v):
            return v
        
        # Check if it's a valid YouTube URL
        patterns = [
            r'youtube\.com\/watch\?v=[a-zA-Z0-9_-]{11}',
            r'youtu\.be\/[a-zA-Z0-9_-]{11}',
            r'youtube\.com\/embed\/[a-zA-Z0-9_-]{11}',
            r'youtube\.com\/live\/[a-zA-Z0-9_-]{11}',
        ]
        
        for pattern in patterns:
            if re.search(pattern, v):
                return v
        
        raise ValueError("Invalid YouTube URL or video ID")


class LivestreamUpdate(BaseModel):
    """Schema for updating a livestream."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    channel: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_live: Optional[bool] = None


class LivestreamResponse(BaseModel):
    """Livestream response schema."""
    
    id: int
    youtube_video_id: str
    name: str
    channel: str
    description: Optional[str]
    url: str
    is_live: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class LivestreamRanked(BaseModel):
    """Livestream with ranking information."""
    
    id: int
    youtube_video_id: str
    name: str
    channel: str
    description: Optional[str]
    url: str
    is_live: bool
    rank: int
    trend_score: float = Field(..., ge=0, le=100)
    current_viewers: Optional[int] = None
    last_updated: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class LivestreamListResponse(BaseModel):
    """Response for ranked livestreams list."""
    
    items: List[LivestreamRanked]
    total: int
    cached_at: datetime
    cache_ttl_seconds: int
