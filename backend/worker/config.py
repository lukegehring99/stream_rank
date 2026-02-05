"""Worker configuration."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Worker-specific settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Database
    database_url: str = "mysql+asyncmy://streamrank:streamrank@localhost:3306/streamrank"
    
    # YouTube API
    youtube_api_key: str = ""
    
    # Polling
    poll_interval_minutes: int = 3
    
    # Data retention
    retention_days: int = 30
    
    # Logging
    log_level: str = "INFO"
    
    # Batch size for YouTube API requests
    youtube_batch_size: int = 50
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 5


@lru_cache
def get_worker_settings() -> WorkerSettings:
    """Get cached worker settings."""
    return WorkerSettings()
