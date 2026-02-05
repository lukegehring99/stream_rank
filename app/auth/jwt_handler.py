"""
JWT Token Handler
=================

Creation and validation of JWT access tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pydantic import BaseModel

from app.config import get_settings


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str  # Subject (username)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at time
    type: str = "access"  # Token type


class JWTHandler:
    """
    Handles JWT token creation and validation.
    
    Uses HS256 algorithm with configurable secret and expiry.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: Optional[str] = None,
        expire_minutes: Optional[int] = None,
    ):
        """
        Initialize JWT handler.
        
        Args:
            secret_key: Secret key for signing (defaults to settings)
            algorithm: JWT algorithm (defaults to settings)
            expire_minutes: Token expiration in minutes (defaults to settings)
        """
        settings = get_settings()
        self.secret_key = secret_key or settings.jwt_secret_key
        self.algorithm = algorithm or settings.jwt_algorithm
        self.expire_minutes = expire_minutes or settings.jwt_access_token_expire_minutes
    
    def create_access_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a new JWT access token.
        
        Args:
            subject: Token subject (typically username)
            expires_delta: Custom expiration time (optional)
        
        Returns:
            Encoded JWT token string
        """
        now = datetime.now(timezone.utc)
        
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.expire_minutes)
        
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "type": "access",
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            TokenPayload if valid, None if invalid/expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def verify_token(self, token: str) -> bool:
        """
        Verify a JWT token is valid.
        
        Args:
            token: JWT token string
        
        Returns:
            True if valid, False otherwise
        """
        return self.decode_token(token) is not None


# Global handler instance
_jwt_handler: Optional[JWTHandler] = None


def get_jwt_handler() -> JWTHandler:
    """Get the global JWT handler instance."""
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler()
    return _jwt_handler


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a new JWT access token.
    
    Convenience function using the global handler.
    
    Args:
        subject: Token subject (typically username)
        expires_delta: Custom expiration time (optional)
    
    Returns:
        Encoded JWT token string
    """
    handler = get_jwt_handler()
    return handler.create_access_token(subject, expires_delta)


def decode_access_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.
    
    Convenience function using the global handler.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenPayload if valid, None if invalid/expired
    """
    handler = get_jwt_handler()
    return handler.decode_token(token)


async def get_current_user(token: str) -> Optional[str]:
    """
    Extract the current user from a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Username if token is valid, None otherwise
    """
    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload.sub
