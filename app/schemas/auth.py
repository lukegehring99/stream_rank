"""
Authentication Schemas
======================

Request and response schemas for authentication endpoints.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request with username and password."""
    
    username: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Admin username",
        examples=["admin"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Admin password",
        examples=["password123"],
    )


class TokenResponse(BaseModel):
    """JWT token response."""
    
    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds",
    )


class LoginResponse(TokenResponse):
    """Login response with user information."""
    
    username: str = Field(
        ...,
        description="Authenticated username",
    )
