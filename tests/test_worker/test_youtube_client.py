"""
Tests for YouTube API client.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from worker.config import WorkerSettings
from worker.youtube_client import (
    YouTubeClient,
    VideoStats,
    YouTubeAPIError,
    QuotaExceededError,
    RateLimitError,
    VideoNotFoundError,
)


@pytest.fixture
def settings(monkeypatch) -> WorkerSettings:
    """Create test settings."""
    monkeypatch.setenv("YOUTUBE_API_KEY", "test_api_key_12345678901234")
    from worker.config import get_worker_settings
    get_worker_settings.cache_clear()
    
    return WorkerSettings(
        youtube_batch_size=50,
        max_retries=2,
        initial_backoff_seconds=0.1,  # Minimum allowed
        max_backoff_seconds=1.0,  # Minimum allowed
    )


class TestVideoStats:
    """Tests for VideoStats dataclass."""
    
    def test_creation(self):
        """Test VideoStats creation."""
        stats = VideoStats(
            video_id="abc12345678",
            view_count=1000,
            is_live=True,
            title="Test Video",
            channel_title="Test Channel",
        )
        
        assert stats.video_id == "abc12345678"
        assert stats.view_count == 1000
        assert stats.is_live is True
        assert stats.title == "Test Video"
        assert stats.channel_title == "Test Channel"
        assert stats.fetched_at is not None
    
    def test_auto_timestamp(self):
        """Test that fetched_at is auto-populated."""
        before = datetime.utcnow()
        stats = VideoStats(video_id="abc", view_count=100, is_live=True)
        after = datetime.utcnow()
        
        assert before <= stats.fetched_at <= after


class TestYouTubeClient:
    """Tests for YouTubeClient class."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, settings: WorkerSettings):
        """Test async context manager."""
        async with YouTubeClient(settings) as client:
            assert client._client is not None
        
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_start_and_close(self, settings: WorkerSettings):
        """Test start and close methods."""
        client = YouTubeClient(settings)
        
        assert client._client is None
        
        await client.start()
        assert client._client is not None
        
        await client.close()
        assert client._client is None
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_video_stats_success(self, settings: WorkerSettings):
        """Test successful video stats fetch."""
        response_data = {
            "items": [
                {
                    "id": "abc12345678",
                    "snippet": {
                        "title": "Live Stream",
                        "channelTitle": "Test Channel",
                    },
                    "statistics": {
                        "viewCount": "5000",
                    },
                    "liveStreamingDetails": {
                        "actualStartTime": "2024-01-01T00:00:00Z",
                        "concurrentViewers": "1500",
                    },
                }
            ]
        }
        
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(200, json=response_data)
        )
        
        async with YouTubeClient(settings) as client:
            stats = await client.get_video_stats("abc12345678")
        
        assert stats is not None
        assert stats.video_id == "abc12345678"
        assert stats.view_count == 1500  # Uses concurrent viewers for live
        assert stats.is_live is True
        assert stats.title == "Live Stream"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_video_stats_not_live(self, settings: WorkerSettings):
        """Test video stats for non-live video."""
        response_data = {
            "items": [
                {
                    "id": "abc12345678",
                    "snippet": {
                        "title": "Past Stream",
                        "channelTitle": "Test Channel",
                    },
                    "statistics": {
                        "viewCount": "10000",
                    },
                    "liveStreamingDetails": {
                        "actualStartTime": "2024-01-01T00:00:00Z",
                        "actualEndTime": "2024-01-01T02:00:00Z",
                    },
                }
            ]
        }
        
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(200, json=response_data)
        )
        
        async with YouTubeClient(settings) as client:
            stats = await client.get_video_stats("abc12345678")
        
        assert stats is not None
        assert stats.is_live is False
        assert stats.view_count == 10000  # Uses total views
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_video_stats_not_found(self, settings: WorkerSettings):
        """Test video not found."""
        response_data = {"items": []}
        
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(200, json=response_data)
        )
        
        async with YouTubeClient(settings) as client:
            stats = await client.get_video_stats("nonexistent")
        
        assert stats is None
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_videos_stats_batch(self, settings: WorkerSettings):
        """Test batch video stats fetch."""
        response_data = {
            "items": [
                {
                    "id": "video1",
                    "snippet": {"title": "Video 1", "channelTitle": "Channel 1"},
                    "statistics": {"viewCount": "1000"},
                    "liveStreamingDetails": {},
                },
                {
                    "id": "video2",
                    "snippet": {"title": "Video 2", "channelTitle": "Channel 2"},
                    "statistics": {"viewCount": "2000"},
                    "liveStreamingDetails": {},
                },
            ]
        }
        
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(200, json=response_data)
        )
        
        async with YouTubeClient(settings) as client:
            stats_list = await client.get_videos_stats(["video1", "video2"])
        
        assert len(stats_list) == 2
        assert stats_list[0].video_id == "video1"
        assert stats_list[1].video_id == "video2"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_quota_exceeded(self, settings: WorkerSettings):
        """Test quota exceeded handling."""
        error_response = {
            "error": {
                "errors": [
                    {"reason": "quotaExceeded", "message": "Quota exceeded"}
                ]
            }
        }
        
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(403, json=error_response)
        )
        
        async with YouTubeClient(settings) as client:
            with pytest.raises(QuotaExceededError):
                await client.get_video_stats("abc12345678")
            
            assert client.is_quota_exceeded is True
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_retry(self, settings: WorkerSettings):
        """Test rate limit with retry."""
        call_count = 0
        
        def mock_response(request):
            nonlocal call_count
            call_count += 1
            
            if call_count < 2:
                return httpx.Response(429, json={"error": "Too many requests"})
            else:
                return httpx.Response(200, json={"items": []})
        
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            side_effect=mock_response
        )
        
        async with YouTubeClient(settings) as client:
            stats = await client.get_video_stats("abc12345678")
        
        assert stats is None  # Empty items
        assert call_count == 2  # Retried once
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_max_retries_exceeded(self, settings: WorkerSettings):
        """Test max retries exceeded."""
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )
        
        async with YouTubeClient(settings) as client:
            # get_video_stats catches errors and returns None
            stats = await client.get_video_stats("abc12345678")
            assert stats is None
        
        # Should have tried max_retries + 1 times
        assert len(respx.calls) == settings.max_retries + 1
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_request_count_tracking(self, settings: WorkerSettings):
        """Test request count tracking."""
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        
        async with YouTubeClient(settings) as client:
            assert client.request_count == 0
            
            await client.get_video_stats("video1")
            assert client.request_count == 1
            
            await client.get_videos_stats(["video2", "video3"])
            assert client.request_count == 2
    
    @pytest.mark.asyncio
    async def test_client_not_started_error(self, settings: WorkerSettings):
        """Test error when client not started."""
        client = YouTubeClient(settings)
        
        with pytest.raises(RuntimeError, match="Client not started"):
            await client.get_video_stats("abc12345678")
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_batching_large_request(self, settings: WorkerSettings):
        """Test that large requests are batched."""
        settings.youtube_batch_size = 5
        
        respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        
        # Request 12 videos - should result in 3 batches
        video_ids = [f"video{i:02d}" for i in range(12)]
        
        async with YouTubeClient(settings) as client:
            await client.get_videos_stats(video_ids)
        
        # Should have made 3 API calls (5 + 5 + 2)
        assert len(respx.calls) == 3
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_video_list(self, settings: WorkerSettings):
        """Test empty video list."""
        async with YouTubeClient(settings) as client:
            stats = await client.get_videos_stats([])
        
        assert stats == []
        assert len(respx.calls) == 0
