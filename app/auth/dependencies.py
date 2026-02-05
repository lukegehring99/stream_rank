"""
Authentication Dependencies
============================

FastAPI dependencies for JWT authentication.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.jwt_handler import decode_access_token, TokenPayload


# HTTP Bearer token extractor
bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="Enter your JWT access token",
    auto_error=True,
)


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> TokenPayload:
    """
    Extract and validate JWT token from request.
    
    Args:
        credentials: HTTP Authorization credentials
    
    Returns:
        Validated token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_username(
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
) -> str:
    """
    Get the current authenticated username.
    
    Args:
        payload: Validated token payload
    
    Returns:
        Username from token
    """
    return payload.sub


async def require_admin(
    username: Annotated[str, Depends(get_current_username)],
) -> str:
    """
    Require admin authentication for protected endpoints.
    
    This dependency can be extended to check admin roles/permissions
    if needed in the future.
    
    Args:
        username: Authenticated username
    
    Returns:
        Validated admin username
    """
    # Currently all authenticated users are considered admins
    # This can be extended to check user roles from database
    return username


# Type alias for dependency injection
CurrentUser = Annotated[str, Depends(require_admin)]
