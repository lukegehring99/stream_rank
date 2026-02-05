"""
Trending YouTube Livestreams - FastAPI Application
==================================================

Production-ready FastAPI backend for tracking and ranking
YouTube livestreams by viewership.

Features:
    - Public API for trending livestreams with caching
    - Admin API with JWT authentication
    - Async SQLAlchemy with MySQL
    - Thread-safe in-memory caching
    - CORS support

Usage:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Environment Variables:
    DATABASE_URL: MySQL connection string
    JWT_SECRET_KEY: Secret for JWT signing (min 32 chars)
    CACHE_TTL_SECONDS: Cache TTL (default: 300)
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import get_settings
from app.db import init_database, close_database
from app.api import public_router, admin_router, auth_router
from app.services.user_service import sync_user_passwords


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database connection pool
    - Shutdown: Close database connections
    """
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Debug mode: {settings.debug}")
    
    await init_database()
    print("Database connection initialized")
    
    # Sync user passwords from environment variables
    await sync_user_passwords()
    print("User passwords synchronized from environment")
    
    yield
    
    # Shutdown
    await close_database()
    print("Database connection closed")


def create_application() -> FastAPI:
    """
    Application factory function.
    
    Creates and configures the FastAPI application with:
    - OpenAPI documentation
    - CORS middleware
    - Exception handlers
    - Route registration
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## Trending YouTube Livestreams API

Track and rank YouTube livestreams by concurrent viewership.

### Features
- **Real-time Rankings**: Get trending livestreams ranked by viewer count
- **Admin Management**: Full CRUD operations for livestream management
- **Viewership Analytics**: Historical viewer count data

### Authentication
Admin endpoints require JWT Bearer token authentication.
Use `/auth/login` to obtain an access token.
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        debug=settings.debug,
    )
    
    # =========================================================================
    # Middleware
    # =========================================================================
    
    # CORS - Allow all origins (as per requirements)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # =========================================================================
    # Exception Handlers
    # =========================================================================
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle request validation errors with detailed messages."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": errors,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        # Log the exception in production
        if not settings.debug:
            # In production, don't expose internal error details
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )
        
        # In debug mode, include exception details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    
    # =========================================================================
    # Route Registration
    # =========================================================================
    
    # Public routes (no authentication required)
    app.include_router(
        public_router,
        prefix="/api/v1",
    )
    
    # Authentication routes
    app.include_router(
        auth_router,
        prefix="/api/v1",
    )
    
    # Admin routes (JWT protected)
    app.include_router(
        admin_router,
        prefix="/api/v1",
    )
    
    # =========================================================================
    # Root Endpoint
    # =========================================================================
    
    @app.get(
        "/",
        include_in_schema=False,
    )
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }
    
    return app


# Create the application instance
app = create_application()


# ============================================================================
# Development Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
