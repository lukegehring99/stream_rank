"""
YouTube Data API Client
=======================

Async client for fetching video statistics from YouTube Data API v3.
Implements rate limiting, exponential backoff, and batch requests.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from worker.config import WorkerSettings, get_worker_settings


logger = logging.getLogger(__name__)


@dataclass
class VideoStats:
    """Video statistics from YouTube API."""
    video_id: str
    view_count: int
    is_live: bool
    title: Optional[str] = None
    channel_title: Optional[str] = None
    fetched_at: datetime = None
    
    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.utcnow()


class YouTubeAPIError(Exception):
    """Base exception for YouTube API errors."""
    pass


class QuotaExceededError(YouTubeAPIError):
    """Raised when YouTube API quota is exceeded."""
    pass


class RateLimitError(YouTubeAPIError):
    """Raised when rate limited by YouTube API."""
    pass


class VideoNotFoundError(YouTubeAPIError):
    """Raised when a video is not found or not accessible."""
    pass


class YouTubeClient:
    """
    Async YouTube Data API v3 client.
    
    Features:
    - Batch requests for efficiency (up to 50 video IDs)
    - Exponential backoff on errors
    - Quota exceeded handling
    - Rate limit safety
    """
    
    def __init__(self, settings: Optional[WorkerSettings] = None):
        """
        Initialize YouTube client.
        
        Args:
            settings: Worker settings (uses default if not provided)
        """
        self.settings = settings or get_worker_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._quota_exceeded = False
        self._quota_reset_time: Optional[datetime] = None
    
    async def __aenter__(self) -> "YouTubeClient":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def start(self) -> None:
        """Initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "Accept": "application/json",
                },
            )
            logger.info("YouTube API client started")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("YouTube API client closed")
    
    def _check_quota(self) -> None:
        """Check if quota is exceeded and raise if so."""
        if self._quota_exceeded:
            if self._quota_reset_time and datetime.utcnow() >= self._quota_reset_time:
                # Reset quota flag after reset time
                self._quota_exceeded = False
                self._quota_reset_time = None
                logger.info("YouTube API quota reset, resuming operations")
            else:
                raise QuotaExceededError(
                    "YouTube API quota exceeded. Will retry after midnight Pacific Time."
                )
    
    async def _make_request(
        self,
        endpoint: str,
        params: dict,
        retry_count: int = 0,
    ) -> dict:
        """
        Make an API request with exponential backoff.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            retry_count: Current retry attempt
            
        Returns:
            JSON response data
            
        Raises:
            YouTubeAPIError: On API errors
            QuotaExceededError: When quota is exceeded
        """
        if self._client is None:
            raise RuntimeError("Client not started. Call start() first.")
        
        self._check_quota()
        
        url = f"{self.settings.youtube_api_base_url}/{endpoint}"
        params["key"] = self.settings.youtube_api_key
        
        try:
            response = await self._client.get(url, params=params)
            self._request_count += 1
            
            if response.status_code == 200:
                return response.json()
            
            # Handle specific error codes
            if response.status_code == 403:
                error_data = response.json()
                errors = error_data.get("error", {}).get("errors", [])
                
                for error in errors:
                    reason = error.get("reason", "")
                    
                    if reason == "quotaExceeded":
                        self._quota_exceeded = True
                        # YouTube quota resets at midnight Pacific Time
                        logger.error("YouTube API quota exceeded")
                        raise QuotaExceededError("Daily quota exceeded")
                    
                    if reason in ("rateLimitExceeded", "userRateLimitExceeded"):
                        raise RateLimitError("Rate limit exceeded")
                
                raise YouTubeAPIError(f"Forbidden: {response.text}")
            
            if response.status_code == 404:
                raise VideoNotFoundError("Video not found")
            
            if response.status_code == 429:
                raise RateLimitError("Too many requests")
            
            if response.status_code >= 500:
                # Server error - retry with backoff
                raise YouTubeAPIError(f"Server error: {response.status_code}")
            
            raise YouTubeAPIError(f"API error {response.status_code}: {response.text}")
        
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error: {e}")
            raise YouTubeAPIError(f"Network error: {e}") from e
        
        except (RateLimitError, YouTubeAPIError) as e:
            # Retry with exponential backoff
            if retry_count < self.settings.max_retries:
                backoff = min(
                    self.settings.initial_backoff_seconds * (2 ** retry_count),
                    self.settings.max_backoff_seconds,
                )
                logger.warning(
                    f"Request failed, retrying in {backoff:.1f}s "
                    f"(attempt {retry_count + 1}/{self.settings.max_retries}): {e}"
                )
                await asyncio.sleep(backoff)
                return await self._make_request(endpoint, params, retry_count + 1)
            raise
    
    async def get_video_stats(self, video_id: str) -> Optional[VideoStats]:
        """
        Get statistics for a single video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            VideoStats or None if video not found
        """
        stats_list = await self.get_videos_stats([video_id])
        return stats_list[0] if stats_list else None
    
    async def get_videos_stats(self, video_ids: list[str]) -> list[VideoStats]:
        """
        Get statistics for multiple videos in batches.
        
        This is the most efficient way to fetch multiple videos as YouTube API
        supports up to 50 video IDs per request.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            List of VideoStats (may be shorter than input if some videos not found)
        """
        if not video_ids:
            return []
        
        all_stats: list[VideoStats] = []
        
        # Process in batches of up to 50 (YouTube API limit)
        batch_size = self.settings.youtube_batch_size
        
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            batch_stats = await self._fetch_videos_batch(batch)
            all_stats.extend(batch_stats)
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(video_ids):
                await asyncio.sleep(0.1)
        
        return all_stats
    
    async def _fetch_videos_batch(self, video_ids: list[str]) -> list[VideoStats]:
        """
        Fetch a single batch of video statistics.
        
        Args:
            video_ids: List of video IDs (max 50)
            
        Returns:
            List of VideoStats for found videos
        """
        params = {
            "part": "snippet,statistics,liveStreamingDetails",
            "id": ",".join(video_ids),
        }
        
        try:
            data = await self._make_request("videos", params)
        except VideoNotFoundError:
            logger.warning(f"Videos not found: {video_ids}")
            return []
        except QuotaExceededError:
            # Re-raise quota errors to stop processing
            raise
        except YouTubeAPIError as e:
            logger.error(f"Failed to fetch videos {video_ids}: {e}")
            return []
        
        stats_list: list[VideoStats] = []
        
        for item in data.get("items", []):
            try:
                video_id = item["id"]
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                live_details = item.get("liveStreamingDetails", {})
                
                # Determine if currently live
                # A video is live if it has actualStartTime but no actualEndTime
                is_live = (
                    "actualStartTime" in live_details
                    and "actualEndTime" not in live_details
                )
                
                # Get view count (live concurrent viewers or total views)
                # For live streams, concurrentViewers is the real-time count.
                # If YouTube omits concurrentViewers when it is 0, default to 0
                # instead of falling back to total viewCount.
                if is_live:
                    view_count = int(live_details.get("concurrentViewers", 0) or 0)
                else:
                    view_count = int(statistics.get("viewCount", 0))
                
                stats = VideoStats(
                    video_id=video_id,
                    view_count=view_count,
                    is_live=is_live,
                    title=snippet.get("title"),
                    channel_title=snippet.get("channelTitle"),
                )
                stats_list.append(stats)
                
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse video data: {e}")
                continue
        
        logger.debug(f"Fetched stats for {len(stats_list)}/{len(video_ids)} videos")
        return stats_list
    
    @property
    def request_count(self) -> int:
        """Total number of API requests made."""
        return self._request_count
    
    @property
    def is_quota_exceeded(self) -> bool:
        """Whether quota is currently exceeded."""
        return self._quota_exceeded
