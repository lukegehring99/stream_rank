"""
YouTube Service
===============

Service for validating and fetching YouTube video metadata.
Used by the API to validate videos before creating livestream entries.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import get_settings


logger = logging.getLogger(__name__)


@dataclass
class YouTubeVideoInfo:
    """YouTube video metadata."""
    video_id: str
    title: str
    channel_title: str
    is_live: bool
    view_count: int = 0


class YouTubeValidationError(Exception):
    """Raised when YouTube video validation fails."""
    pass


class YouTubeService:
    """
    Service for validating YouTube videos.
    
    Used to verify that a YouTube video exists and fetch its metadata
    before creating a livestream entry.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._api_base_url = "https://www.googleapis.com/youtube/v3"
    
    async def get_video_info(self, video_id: str) -> Optional[YouTubeVideoInfo]:
        """
        Fetch video information from YouTube API.
        
        Args:
            video_id: YouTube video ID (11 characters)
            
        Returns:
            YouTubeVideoInfo if video exists, None otherwise
            
        Raises:
            YouTubeValidationError: If API call fails
        """
        if not self.settings.youtube_api_key:
            logger.warning("YouTube API key not configured, skipping validation")
            return None
        
        params = {
            "part": "snippet,statistics,liveStreamingDetails",
            "id": video_id,
            "key": self.settings.youtube_api_key,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self._api_base_url}/videos",
                    params=params,
                )
                
                if response.status_code == 403:
                    error_data = response.json()
                    errors = error_data.get("error", {}).get("errors", [])
                    for error in errors:
                        if error.get("reason") == "quotaExceeded":
                            logger.warning("YouTube API quota exceeded, skipping validation")
                            return None
                    raise YouTubeValidationError("YouTube API access forbidden")
                
                if response.status_code != 200:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    raise YouTubeValidationError(f"YouTube API error: {response.status_code}")
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    # Video not found
                    return None
                
                item = items[0]
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                live_details = item.get("liveStreamingDetails", {})
                
                # Determine if video is live
                live_content = snippet.get("liveBroadcastContent", "none")
                is_live = live_content == "live"
                
                # Get view count
                view_count = int(statistics.get("viewCount", 0))
                if is_live:
                    # For live streams, concurrent viewers is in liveStreamingDetails
                    view_count = int(live_details.get("concurrentViewers", view_count))
                
                return YouTubeVideoInfo(
                    video_id=video_id,
                    title=snippet.get("title", "Unknown Title"),
                    channel_title=snippet.get("channelTitle", "Unknown Channel"),
                    is_live=is_live,
                    view_count=view_count,
                )
                
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching video {video_id}")
            raise YouTubeValidationError("YouTube API request timed out")
        except httpx.NetworkError as e:
            logger.error(f"Network error fetching video {video_id}: {e}")
            raise YouTubeValidationError(f"Network error: {e}")
    
    def is_configured(self) -> bool:
        """Check if YouTube API key is configured."""
        return bool(self.settings.youtube_api_key)
    
    async def validate_video_exists(self, video_id: str) -> Optional[YouTubeVideoInfo]:
        """
        Validate that a YouTube video exists.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            YouTubeVideoInfo with video metadata, or None if API key not configured
            
        Raises:
            YouTubeValidationError: If video doesn't exist or API fails
        """
        if not self.is_configured():
            logger.warning("YouTube API key not configured, skipping validation")
            return None
        
        info = await self.get_video_info(video_id)
        
        if info is None:
            raise YouTubeValidationError(
                f"YouTube video '{video_id}' not found or is not accessible"
            )
        
        return info


# Singleton instance
_youtube_service: Optional[YouTubeService] = None


def get_youtube_service() -> YouTubeService:
    """Get or create the YouTube service singleton."""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service
