"""
Dependencies Module
===================

FastAPI dependency injection setup and common dependencies.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_async_session
from app.services import LivestreamService, CacheService, get_cache_service
from app.auth.dependencies import CurrentUser, require_admin


# ============================================================================
# Type Aliases for Dependency Injection
# ============================================================================

# Settings dependency
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Database session dependency
SessionDep = Annotated[AsyncSession, Depends(get_async_session)]

# Cache service dependency
CacheDep = Annotated[CacheService, Depends(get_cache_service)]

# Authenticated user dependency
AdminUserDep = CurrentUser


# ============================================================================
# Service Dependencies
# ============================================================================

async def get_livestream_service_dep(
    session: SessionDep,
) -> LivestreamService:
    """
    Dependency injection for LivestreamService.
    
    Args:
        session: Database session (injected)
    
    Returns:
        LivestreamService instance
    """
    return LivestreamService(session)


LivestreamServiceDep = Annotated[
    LivestreamService, 
    Depends(get_livestream_service_dep)
]


__all__ = [
    "SettingsDep",
    "SessionDep",
    "CacheDep",
    "AdminUserDep",
    "LivestreamServiceDep",
    "get_livestream_service_dep",
]
