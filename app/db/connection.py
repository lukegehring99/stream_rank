"""
Async Database Connection
=========================

SQLAlchemy async engine and session management with connection pooling.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)

from app.config import get_settings


class DatabaseManager:
    """
    Manages async database connections and sessions.
    
    Implements connection pooling and proper session lifecycle management.
    Thread-safe and suitable for use with FastAPI's dependency injection.
    """
    
    _instance: Optional["DatabaseManager"] = None
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    def __new__(cls) -> "DatabaseManager":
        """Singleton pattern - ensure only one DatabaseManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self) -> None:
        """
        Initialize the database engine and session factory.
        
        Creates an async engine with connection pooling configured
        based on application settings.
        """
        if self._engine is not None:
            return  # Already initialized
        
        settings = get_settings()
        
        self._engine = create_async_engine(
            settings.async_database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,  # Enable connection health checks
            echo=settings.db_echo,
        )
        
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    async def close(self) -> None:
        """
        Close the database engine and dispose of all connections.
        
        Should be called during application shutdown.
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.
        
        Provides automatic commit/rollback and session cleanup.
        
        Usage:
            async with db_manager.session() as session:
                result = await session.execute(query)
        
        Yields:
            AsyncSession instance
        """
        if self._session_factory is None:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency injection helper for FastAPI.
        
        Usage:
            @app.get("/items")
            async def get_items(session: AsyncSession = Depends(get_async_session)):
                ...
        
        Yields:
            AsyncSession instance
        """
        if self._session_factory is None:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get the async engine (for advanced operations)."""
        return self._engine
    
    @property
    def is_initialized(self) -> bool:
        """Check if the database manager is initialized."""
        return self._engine is not None


# Global instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get the global DatabaseManager instance.
    
    Returns:
        DatabaseManager singleton instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting a database session.
    
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_async_session)):
            ...
    
    Yields:
        AsyncSession instance with automatic cleanup
    """
    db_manager = get_db_manager()
    async for session in db_manager.get_session():
        yield session


async def init_database() -> None:
    """
    Initialize the database connection.
    
    Call this during application startup.
    """
    db_manager = get_db_manager()
    await db_manager.initialize()


async def close_database() -> None:
    """
    Close the database connection.
    
    Call this during application shutdown.
    """
    db_manager = get_db_manager()
    await db_manager.close()
