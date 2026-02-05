"""
Worker Configuration
====================

Environment-based configuration for the background worker service.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """
    Worker configuration loaded from environment variables.
    
    All settings can be overridden via environment variables or .env file.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # =========================================================================
    # YouTube API Settings
    # =========================================================================
    youtube_api_key: str = Field(
        ...,  # Required - no default
        description="YouTube Data API v3 key",
        alias="YOUTUBE_API_KEY",
    )
    youtube_api_base_url: str = Field(
        default="https://www.googleapis.com/youtube/v3",
        description="YouTube API base URL",
    )
    youtube_batch_size: int = Field(
        default=50,
        ge=1,
        le=50,  # YouTube API max is 50 IDs per request
        description="Number of video IDs per batch request",
    )
    
    # =========================================================================
    # Polling Settings
    # =========================================================================
    poll_interval_minutes: int = Field(
        default=3,
        ge=1,
        le=60,
        description="How often to poll YouTube API (minutes)",
        alias="POLL_INTERVAL_MINUTES",
    )
    
    # =========================================================================
    # Data Retention Settings
    # =========================================================================
    retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to retain viewership history",
        alias="RETENTION_DAYS",
    )
    cleanup_batch_size: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Batch size for cleanup deletions",
    )
    
    # =========================================================================
    # Database Settings
    # =========================================================================
    database_url: str = Field(
        default="mysql+aiomysql://root:password@localhost:3306/stream_rank",
        description="Async SQLAlchemy database URL",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Database connection pool size (smaller for worker)",
    )
    db_max_overflow: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Max overflow connections",
    )
    db_pool_recycle: int = Field(
        default=3600,
        ge=60,
        description="Recycle connections after N seconds",
    )
    
    # =========================================================================
    # Logging Settings
    # =========================================================================
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        alias="LOG_LEVEL",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    
    # =========================================================================
    # Retry Settings
    # =========================================================================
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for API calls",
    )
    initial_backoff_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Initial backoff delay for retries",
    )
    max_backoff_seconds: float = Field(
        default=60.0,
        ge=1.0,
        le=300.0,
        description="Maximum backoff delay",
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v_upper
    
    @property
    def async_database_url(self) -> str:
        """Get the async database URL, converting if necessary."""
        url = self.database_url
        # Convert sync driver to async if needed
        if "mysql+pymysql" in url:
            url = url.replace("mysql+pymysql", "mysql+aiomysql")
        elif "mysql://" in url and "aiomysql" not in url:
            url = url.replace("mysql://", "mysql+aiomysql://")
        return url


@lru_cache
def get_worker_settings() -> WorkerSettings:
    """
    Get cached worker settings.
    
    Returns:
        WorkerSettings instance with values from environment
    """
    return WorkerSettings()
