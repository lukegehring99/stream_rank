"""YouTube Data API v3 client."""
import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class VideoStats:
    """Statistics for a YouTube video."""
    
    video_id: str
    view_count: int
    is_live: bool
    concurrent_viewers: Optional[int] = None
    title: Optional[str] = None
    channel_title: Optional[str] = None


class YouTubeAPIError(Exception):
    """Base exception for YouTube API errors."""
    pass


class QuotaExceededError(YouTubeAPIError):
    """Raised when API quota is exceeded."""
    pass


class YouTubeClient:
    """Async client for YouTube Data API v3."""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        batch_size: int = 50,
    ):
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.batch_size = batch_size
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self) -> "YouTubeClient":
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._session.close()
            self._session = None
    
    async def get_video_stats(self, video_ids: List[str]) -> List[VideoStats]:
        """Get statistics for multiple videos.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            List of VideoStats for each video
        """
        if not video_ids:
            return []
        
        all_stats = []
        
        # Process in batches
        for i in range(0, len(video_ids), self.batch_size):
            batch = video_ids[i:i + self.batch_size]
            stats = await self._fetch_batch(batch)
            all_stats.extend(stats)
        
        return all_stats
    
    async def _fetch_batch(self, video_ids: List[str]) -> List[VideoStats]:
        """Fetch stats for a batch of videos."""
        params = {
            "part": "snippet,statistics,liveStreamingDetails",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }
        
        for attempt in range(self.max_retries):
            try:
                data = await self._make_request("videos", params)
                return self._parse_response(data)
            
            except QuotaExceededError:
                logger.error("YouTube API quota exceeded")
                raise
            
            except Exception as e:
                logger.warning(
                    f"YouTube API request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
                else:
                    raise
        
        return []
    
    async def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make an API request with error handling."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with self._session.get(url, params=params) as response:
            data = await response.json()
            
            if response.status == 403:
                error = data.get("error", {})
                errors = error.get("errors", [])
                
                for err in errors:
                    if err.get("reason") == "quotaExceeded":
                        raise QuotaExceededError("YouTube API quota exceeded")
                
                raise YouTubeAPIError(f"Forbidden: {error.get('message', 'Unknown error')}")
            
            if response.status != 200:
                raise YouTubeAPIError(
                    f"API request failed with status {response.status}: {data}"
                )
            
            return data
    
    def _parse_response(self, data: Dict) -> List[VideoStats]:
        """Parse API response into VideoStats objects."""
        stats = []
        
        for item in data.get("items", []):
            video_id = item["id"]
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            live_details = item.get("liveStreamingDetails", {})
            
            # Determine if live and get viewers
            is_live = "concurrentViewers" in live_details
            concurrent_viewers = None
            
            if is_live:
                concurrent_viewers = int(live_details.get("concurrentViewers", 0))
            
            # Get view count (total views, not concurrent)
            view_count = int(statistics.get("viewCount", 0))
            
            # For live streams, use concurrent viewers if available
            if concurrent_viewers is not None:
                view_count = concurrent_viewers
            
            stats.append(VideoStats(
                video_id=video_id,
                view_count=view_count,
                is_live=is_live,
                concurrent_viewers=concurrent_viewers,
                title=snippet.get("title"),
                channel_title=snippet.get("channelTitle"),
            ))
        
        return stats
    
    async def get_single_video(self, video_id: str) -> Optional[VideoStats]:
        """Get stats for a single video."""
        stats = await self.get_video_stats([video_id])
        return stats[0] if stats else None
