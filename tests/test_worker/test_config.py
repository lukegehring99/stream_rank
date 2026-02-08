"""
Tests for worker configuration.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from worker.config import WorkerSettings, get_worker_settings


class TestWorkerSettings:
    """Tests for WorkerSettings class."""
    
    def test_default_values(self, monkeypatch):
        """Test default configuration values."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        get_worker_settings.cache_clear()
        
        settings = WorkerSettings()
        
        assert settings.poll_interval_minutes == 3
        assert settings.retention_days == 30
        assert settings.cleanup_batch_size == 1000
        assert settings.youtube_batch_size == 50
        assert settings.log_level == "INFO"
        assert settings.max_retries == 3
    
    def test_youtube_api_key_required(self, monkeypatch):
        """Test that YouTube API key is required."""
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        get_worker_settings.cache_clear()
        
        # Create a settings class that doesn't read from .env file
        with pytest.raises(ValidationError):
            WorkerSettings(_env_file=None)  # Disable .env file reading
    
    def test_poll_interval_validation(self, monkeypatch):
        """Test poll interval validation."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        get_worker_settings.cache_clear()
        
        # Valid values
        monkeypatch.setenv("POLL_INTERVAL_MINUTES", "5")
        settings = WorkerSettings()
        assert settings.poll_interval_minutes == 5
        
        # Too low
        monkeypatch.setenv("POLL_INTERVAL_MINUTES", "0")
        with pytest.raises(ValidationError):
            WorkerSettings()
        
        # Too high
        monkeypatch.setenv("POLL_INTERVAL_MINUTES", "100")
        with pytest.raises(ValidationError):
            WorkerSettings()
    
    def test_retention_days_validation(self, monkeypatch):
        """Test retention days validation."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        monkeypatch.setenv("RETENTION_DAYS", "7")
        get_worker_settings.cache_clear()
        
        settings = WorkerSettings()
        assert settings.retention_days == 7
        
        monkeypatch.setenv("RETENTION_DAYS", "0")
        with pytest.raises(ValidationError):
            WorkerSettings()
    
    def test_log_level_validation(self, monkeypatch):
        """Test log level validation."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        get_worker_settings.cache_clear()
        
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            monkeypatch.setenv("LOG_LEVEL", level)
            settings = WorkerSettings()
            assert settings.log_level == level
        
        # Case insensitive
        monkeypatch.setenv("LOG_LEVEL", "debug")
        settings = WorkerSettings()
        assert settings.log_level == "DEBUG"
        
        # Invalid level
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        with pytest.raises(ValidationError):
            WorkerSettings()
    
    def test_async_database_url_conversion(self, monkeypatch):
        """Test database URL conversion to async."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        get_worker_settings.cache_clear()
        
        # Already async
        monkeypatch.setenv("DATABASE_URL", "mysql+aiomysql://user:pass@localhost/db")
        settings = WorkerSettings()
        assert settings.async_database_url == "mysql+aiomysql://user:pass@localhost/db"
        
        # Sync pymysql
        monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://user:pass@localhost/db")
        settings = WorkerSettings()
        assert settings.async_database_url == "mysql+aiomysql://user:pass@localhost/db"
        
        # Plain mysql
        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")
        settings = WorkerSettings()
        assert settings.async_database_url == "mysql+aiomysql://user:pass@localhost/db"
    
    def test_youtube_batch_size_validation(self, monkeypatch):
        """Test YouTube batch size validation."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_12345678901234567890")
        get_worker_settings.cache_clear()
        
        settings = WorkerSettings(youtube_batch_size=25)
        assert settings.youtube_batch_size == 25
        
        # Max is 50 (YouTube API limit)
        with pytest.raises(ValidationError):
            WorkerSettings(youtube_batch_size=100)
    
    def test_environment_variable_aliases(self, monkeypatch):
        """Test that environment variable aliases work."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "env_api_key_12345678901234")
        monkeypatch.setenv("POLL_INTERVAL_MINUTES", "5")
        monkeypatch.setenv("RETENTION_DAYS", "14")
        monkeypatch.setenv("DATABASE_URL", "mysql://localhost/test")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        # Clear the lru_cache to reload settings
        get_worker_settings.cache_clear()
        settings = WorkerSettings()
        
        assert settings.youtube_api_key == "env_api_key_12345678901234"
        assert settings.poll_interval_minutes == 5
        assert settings.retention_days == 14
        assert settings.log_level == "DEBUG"


class TestGetWorkerSettings:
    """Tests for get_worker_settings function."""
    
    def test_caching(self, monkeypatch):
        """Test that settings are cached."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key_for_caching_123")
        get_worker_settings.cache_clear()
        
        settings1 = get_worker_settings()
        settings2 = get_worker_settings()
        
        assert settings1 is settings2
