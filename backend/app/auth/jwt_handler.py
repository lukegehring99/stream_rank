"""JWT token handling."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pydantic import BaseModel

from app.config import get_settings


class JWTHandler:
    """Handles JWT token creation and validation."""
    
    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        expiry_hours: int = 24,
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.expiry_hours = expiry_hours
    
    def create_token(self, username: str) -> tuple[str, datetime]:
        """Create a new JWT token.
        
        Returns:
            Tuple of (token, expires_at)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.expiry_hours)
        
        payload = {
            "sub": username,
            "iat": now,
            "exp": expires_at,
        }
        
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, expires_at
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token.
        
        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_username_from_token(self, token: str) -> Optional[str]:
        """Extract username from a valid token."""
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")
        return None


def create_jwt_handler() -> JWTHandler:
    """Create JWT handler with settings from environment."""
    settings = get_settings()
    return JWTHandler(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expiry_hours=settings.jwt_expiry_hours,
    )
