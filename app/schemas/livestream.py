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
    
    youtube_video_id: Optional[str] = Field(
        default=None,
        min_length=11,
        max_length=11,
        description="YouTube video ID (11 characters)",
        examples=["dQw4w9WgXcQ"],
    )
    youtube_url: Optional[str] = Field(
        default=None,
        description="YouTube video URL (alternative to video ID)",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Livestream title",
        examples=["Live Science Experiment #42"],
    )
    channel: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Channel name",
        examples=["ScienceChannel"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Stream description",
    )
    is_live: bool = Field(
        default=False,
        description="Whether the stream is currently live",
    )
    
    @field_validator("youtube_video_id")
    @classmethod
    def validate_video_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate YouTube video ID format."""
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9_-]{11}$", v):
            raise ValueError("Invalid YouTube video ID format")
        return v
    
    @model_validator(mode="after")
    def validate_youtube_input(self) -> "LivestreamCreate":
        """Ensure either video ID or URL is provided, and extract ID from URL."""
        if self.youtube_video_id is None and self.youtube_url is None:
            raise ValueError("Either youtube_video_id or youtube_url must be provided")
        
        if self.youtube_url and self.youtube_video_id is None:
            # Extract video ID from URL
            video_id = self._extract_video_id(self.youtube_url)
            if video_id is None:
                raise ValueError("Could not extract video ID from YouTube URL")
            self.youtube_video_id = video_id
        
        return self
    
    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
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
