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
)
from .common import (
    HealthResponse,
    ErrorResponse,
    PaginatedResponse,
    DashboardStats,
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
    # Common
    "HealthResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "DashboardStats",
]
