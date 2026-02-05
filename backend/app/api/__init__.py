"""API routes module."""
from .public import router as public_router
from .auth import router as auth_router
from .admin import router as admin_router

__all__ = ["public_router", "auth_router", "admin_router"]
