"""
Application Settings
====================

Pydantic-based configuration with environment variable support.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    Environment variables can be set directly or via a .env file.
    All settings have sensible defaults for development.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # =========================================================================
    # Application Settings
    # =========================================================================
    app_name: str = Field(
        default="Trending YouTube Livestreams API",
        description="Application name displayed in docs",
    )
    app_version: str = Field(
        default="1.0.0",
        description="API version",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
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
        default=10,
        ge=1,
        le=100,
        description="Database connection pool size",
    )
    db_max_overflow: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Max overflow connections beyond pool size",
    )
    db_pool_recycle: int = Field(
        default=3600,
        ge=60,
        description="Recycle connections after N seconds",
    )
    db_echo: bool = Field(
        default=False,
        description="Echo SQL statements (for debugging)",
    )
    
    # =========================================================================
    # JWT Authentication Settings
    # =========================================================================
    jwt_secret_key: str = Field(
        default="your-super-secret-key-change-in-production",
        min_length=32,
        description="Secret key for JWT signing (min 32 chars)",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Access token expiration in minutes",
    )
    
    # =========================================================================
    # User Password Settings (for startup sync)
    # =========================================================================
    admin_password: Optional[str] = Field(
        default=None,
        min_length=8,
        description="Admin user password (synced on startup)",
        alias="ADMIN_PASSWORD",
    )
    moderator_password: Optional[str] = Field(
        default=None,
        min_length=8,
        description="Moderator user password (synced on startup)",
        alias="MODERATOR_PASSWORD",
    )
    
    # =========================================================================
    # Cache Settings
    # =========================================================================
    cache_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        ge=30,
        le=3600,
        description="Cache TTL in seconds",
        alias="CACHE_TTL_SECONDS",
    )
    cache_max_items: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum items to store in cache",
    )
    
    # =========================================================================
    # API Settings
    # =========================================================================
    max_livestreams_count: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum livestreams to return in public endpoint",
    )
    default_livestreams_count: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Default livestreams count if not specified",
    )
    
    # =========================================================================
    # YouTube API Settings
    # =========================================================================
    youtube_api_key: Optional[str] = Field(
        default=None,
        description="YouTube Data API v3 key for video validation",
        alias="YOUTUBE_API_KEY",
    )
    
    # =========================================================================
    # CORS Settings
    # =========================================================================
    cors_origins: str = Field(
        default="*",
        description="Allowed CORS origins (comma-separated or '*' for all)",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests",
    )
    cors_allow_methods: list[str] = Field(
        default=["*"],
        description="Allowed HTTP methods",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        description="Allowed HTTP headers",
    )
    
    # =========================================================================
    # Anomaly Detection Settings
    # =========================================================================
    anomaly_algorithm: str = Field(
        default="quantile",
        description="Anomaly detection algorithm: 'quantile' or 'zscore'",
    )
    anomaly_recent_window_minutes: int = Field(
        default=15,
        ge=1,
        description="Recent window in minutes for anomaly detection",
    )
    anomaly_baseline_hours: int = Field(
        default=24,
        ge=1,
        description="Baseline period in hours for anomaly detection",
    )
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Convert CORS origins string to list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Ensure JWT secret is sufficiently long."""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        return v
    
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
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Uses lru_cache for singleton pattern - settings are loaded once
    and reused throughout the application lifecycle.
    
    Returns:
        Settings instance with values from environment
    """
    return Settings()
