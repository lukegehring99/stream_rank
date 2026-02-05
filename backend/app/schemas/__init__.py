"""Pydantic schemas for API requests and responses."""
from .auth import LoginRequest, LoginResponse, TokenPayload
from .livestream import (
    LivestreamBase,
    LivestreamCreate,
    LivestreamUpdate,
    LivestreamResponse,
    LivestreamRanked,
    LivestreamListResponse,
)
from .viewership import ViewershipRecord, ViewershipHistoryResponse
from .common import HealthResponse, ErrorResponse, PaginatedResponse

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "TokenPayload",
    # Livestream
    "LivestreamBase",
    "LivestreamCreate",
    "LivestreamUpdate",
    "LivestreamResponse",
    "LivestreamRanked",
    "LivestreamListResponse",
    # Viewership
    "ViewershipRecord",
    "ViewershipHistoryResponse",
    # Common
    "HealthResponse",
    "ErrorResponse",
    "PaginatedResponse",
]
