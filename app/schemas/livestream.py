"""
Livestream Schemas
==================

Request and response schemas for livestream endpoints.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class LivestreamBase(BaseModel):
    """Base schema with common livestream fields."""
    
    name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Livestream title",
        examples=["Live Science Experiment #42"],
    )
    channel: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Channel name",
        examples=["ScienceChannel"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Stream description",
        examples=["Join us for an exciting live science experiment!"],
    )
    is_live: Optional[bool] = Field(
        default=None,
        description="Whether the stream is currently live",
    )


class LivestreamCreate(BaseModel):
    """Schema for creating a new livestream."""
    
    youtube_url: str = Field(
        ...,
        description="YouTube video URL or video ID",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    )
    
    # These fields are populated from YouTube API, not provided by user
    youtube_video_id: Optional[str] = Field(
        default=None,
        description="Extracted YouTube video ID (auto-populated)",
    )
    name: Optional[str] = Field(
        default=None,
        description="Livestream title (auto-populated from YouTube)",
    )
    channel: Optional[str] = Field(
        default=None,
        description="Channel name (auto-populated from YouTube)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Stream description",
    )
    is_live: Optional[bool] = Field(
        default=None,
        description="Whether the stream is currently live (auto-populated from YouTube)",
    )
    
    @model_validator(mode="after")
    def extract_video_id(self) -> "LivestreamCreate":
        """Extract video ID from URL if not already set."""
        if self.youtube_video_id is None:
            video_id = self._extract_video_id(self.youtube_url)
            if video_id is None:
                raise ValueError("Could not extract video ID from YouTube URL")
            self.youtube_video_id = video_id
        return self
    
    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/live/)([a-zA-Z0-9_-]{11})",
            r"^([a-zA-Z0-9_-]{11})$",  # Just the video ID
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


class LivestreamUpdate(LivestreamBase):
    """Schema for updating a livestream."""
    pass


class LivestreamResponse(BaseModel):
    """Response schema for a single livestream."""
    
    id: str = Field(..., validation_alias="public_id", description="Unique identifier (UUID)")
    youtube_video_id: str = Field(..., description="YouTube video ID")
    name: str = Field(..., description="Livestream title")
    channel: str = Field(..., description="Channel name")
    description: Optional[str] = Field(None, description="Stream description")
    url: str = Field(..., description="Full YouTube URL")
    is_live: bool = Field(..., description="Currently streaming")
    current_viewers: Optional[int] = Field(None, description="Current viewer count")
    peak_viewers: int = Field(0, description="Peak viewer count")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class LivestreamRankedResponse(BaseModel):
    """Response schema for a ranked livestream with viewership data."""
    
    id: str = Field(..., validation_alias="public_id", description="Unique identifier (UUID)")
    youtube_video_id: str = Field(..., description="YouTube video ID")
    name: str = Field(..., description="Livestream title")
    channel: str = Field(..., description="Channel name")
    url: str = Field(..., description="Full YouTube URL")
    is_live: bool = Field(..., description="Currently streaming")
    current_viewers: int = Field(..., description="Current viewer count")
    rank: int = Field(..., description="Rank position (1-based)")
    trend_score: Optional[float] = Field(None, description="Anomaly/trend score (0-100)")
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class LivestreamListResponse(BaseModel):
    """Response schema for a list of livestreams."""
    
    items: list[LivestreamResponse] = Field(..., description="List of livestreams")
    total: int = Field(..., description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(10, description="Items per page")
    total_pages: int = Field(1, description="Total number of pages")


class TrendingLivestreamsResponse(BaseModel):
    """Response schema for trending livestreams (public endpoint)."""
    
    items: list[LivestreamRankedResponse] = Field(
        ..., 
        description="Ranked list of trending livestreams"
    )
    count: int = Field(..., description="Number of items returned")
    cached_at: Optional[datetime] = Field(
        None, 
        description="Cache timestamp (if served from cache)"
    )
