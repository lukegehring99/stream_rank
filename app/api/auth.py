"""
Authentication Routes
=====================

JWT authentication endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.db import get_async_session
from app.models import User
from app.schemas import LoginRequest, LoginResponse
from app.auth import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Admin Login",
    description="Authenticate with username and password to receive a JWT access token.",
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    credentials: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    """
    Authenticate and get a JWT access token.
    
    Args:
        credentials: Login credentials (username and password)
    
    Returns:
        JWT access token with expiration info
    
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Find user by username
    stmt = select(User).where(User.username == credentials.username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Validate credentials
    if user is None or not user.check_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token = create_access_token(subject=user.username)
    expires_in = settings.jwt_access_token_expire_minutes * 60
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        username=user.username,
    )
