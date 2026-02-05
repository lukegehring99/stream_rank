"""Authentication dependencies for FastAPI."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt_handler import JWTHandler, create_jwt_handler


# Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    jwt_handler: JWTHandler = Depends(create_jwt_handler),
) -> Optional[str]:
    """Get current user from JWT token (optional).
    
    Returns:
        Username if valid token provided, None otherwise
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    username = jwt_handler.get_username_from_token(token)
    return username


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    jwt_handler: JWTHandler = Depends(create_jwt_handler),
) -> str:
    """Require valid authentication.
    
    Raises:
        HTTPException: If no valid token provided
        
    Returns:
        Username from token
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    username = jwt_handler.get_username_from_token(token)
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return username
