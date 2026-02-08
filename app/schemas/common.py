"""
Common Schemas
==============

Shared schemas used across multiple endpoints.
"""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(
        default="healthy",
        description="Service status",
        examples=["healthy", "unhealthy"],
    )
    timestamp: datetime = Field(
        ...,
        description="Health check timestamp",
    )
    version: str = Field(
        ...,
        description="API version",
    )
    database: str = Field(
        default="connected",
        description="Database connection status",
        examples=["connected", "disconnected"],
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str = Field(
        ...,
        description="Error message",
        examples=["Resource not found"],
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code",
        examples=["NOT_FOUND", "VALIDATION_ERROR"],
    )


# Generic type for paginated responses
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    
    items: list[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    
    total_streams: int = Field(
        ...,
        description="Total number of tracked livestreams",
    )
    live_streams: int = Field(
        ...,
        description="Number of currently live streams",
    )
    total_viewers: int = Field(
        ...,
        description="Total current viewers across all live streams",
    )
    peak_viewers_today: int = Field(
        ...,
        description="Peak concurrent viewers recorded today",
    )


# ============================================================================
# Anomaly Config Schemas
# ============================================================================

class AnomalyConfigEntry(BaseModel):
    """Single anomaly config entry."""
    
    key: str = Field(
        ...,
        description="Configuration key (dot notation for nested params)",
        examples=["algorithm", "quantile_params.baseline_percentile"],
    )
    type: str = Field(
        ...,
        description="Python type name",
        examples=["str", "int", "float", "bool"],
    )
    value: str = Field(
        ...,
        description="Stringified configuration value",
        examples=["quantile", "75.0", "true"],
    )
    is_default: bool = Field(
        default=True,
        description="Whether this is the default value",
    )


class AnomalyConfigListResponse(BaseModel):
    """List of all anomaly config entries."""
    
    items: list[AnomalyConfigEntry] = Field(
        ...,
        description="List of configuration entries",
    )


class AnomalyConfigUpdateRequest(BaseModel):
    """Request to update an anomaly config value."""
    
    key: str = Field(
        ...,
        description="Configuration key to update",
        examples=["algorithm", "quantile_params.spike_threshold"],
    )
    value: str = Field(
        ...,
        description="New value (will be validated and parsed)",
        examples=["zscore", "2.0"],
    )


class AnomalyConfigUpdateResponse(BaseModel):
    """Response after updating a config value."""
    
    success: bool = Field(
        default=True,
        description="Whether the update succeeded",
    )
    entry: AnomalyConfigEntry = Field(
        ...,
        description="Updated configuration entry",
    )
