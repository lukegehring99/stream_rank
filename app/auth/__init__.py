"""
Authentication Module
=====================

JWT-based authentication for admin endpoints.
"""

from .jwt_handler import (
    JWTHandler,
    create_access_token,
    decode_access_token,
    get_current_user,
    TokenPayload,
)
from .dependencies import require_admin

__all__ = [
    "JWTHandler",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "require_admin",
    "TokenPayload",
]
