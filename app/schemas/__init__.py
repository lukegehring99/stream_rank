"""
Pydantic Schemas
================

Request and response schemas for API endpoints.
"""

from .auth import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
)
from .livestream import (
    LivestreamBase,
    LivestreamCreate,
    LivestreamUpdate,
    LivestreamResponse,
    LivestreamListResponse,
    LivestreamRankedResponse,
    TrendingLivestreamsResponse,
)
from .viewership import (
    ViewershipHistoryResponse,
    ViewershipHistoryListResponse,
    DownsampleInterval,
    DownsampledViewershipResponse,
    DOWNSAMPLE_SECONDS,
    PublicViewershipDataPoint,
    PublicViewershipResponse,
)
from .common import (
    HealthResponse,
    ErrorResponse,
    PaginatedResponse,
    DashboardStats,
    AnomalyConfigEntry,
    AnomalyConfigListResponse,
    AnomalyConfigUpdateRequest,
    AnomalyConfigUpdateResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "TokenResponse",
    # Livestream
    "LivestreamBase",
    "LivestreamCreate",
    "LivestreamUpdate",
    "LivestreamResponse",
    "LivestreamListResponse",
    "LivestreamRankedResponse",
    "TrendingLivestreamsResponse",
    # Viewership
    "ViewershipHistoryResponse",
    "ViewershipHistoryListResponse",
    "DownsampleInterval",
    "DownsampledViewershipResponse",
    "DOWNSAMPLE_SECONDS",
    "PublicViewershipDataPoint",
    "PublicViewershipResponse",
    # Common
    "HealthResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "DashboardStats",
    # Anomaly Config
    "AnomalyConfigEntry",
    "AnomalyConfigListResponse",
    "AnomalyConfigUpdateRequest",
    "AnomalyConfigUpdateResponse",
]
