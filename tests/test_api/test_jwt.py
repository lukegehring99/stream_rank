"""
JWT Handler Tests
=================

Tests for JWT token creation and validation.
"""

import time
from datetime import timedelta

import pytest

from app.auth.jwt_handler import JWTHandler, TokenPayload


class TestJWTHandler:
    """Tests for JWTHandler class."""
    
    @pytest.fixture
    def handler(self) -> JWTHandler:
        """Create a JWT handler with test settings."""
        return JWTHandler(
            secret_key="test-secret-key-that-is-at-least-32-characters-long",
            algorithm="HS256",
            expire_minutes=60,
        )
    
    def test_create_access_token(self, handler: JWTHandler):
        """Should create a valid token."""
        token = handler.create_access_token("testuser")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self, handler: JWTHandler):
        """Should decode a valid token."""
        token = handler.create_access_token("testuser")
        
        payload = handler.decode_token(token)
        
        assert payload is not None
        assert payload.sub == "testuser"
        assert payload.type == "access"
    
    def test_decode_invalid_token(self, handler: JWTHandler):
        """Should return None for invalid token."""
        payload = handler.decode_token("invalid.token.here")
        
        assert payload is None
    
    def test_decode_expired_token(self, handler: JWTHandler):
        """Should return None for expired token."""
        # Create a token that expires in the past
        token = handler.create_access_token(
            "testuser",
            expires_delta=timedelta(seconds=-1),
        )
        
        payload = handler.decode_token(token)
        assert payload is None
    
    def test_verify_valid_token(self, handler: JWTHandler):
        """Should verify a valid token."""
        token = handler.create_access_token("testuser")
        
        assert handler.verify_token(token) is True
    
    def test_verify_invalid_token(self, handler: JWTHandler):
        """Should reject an invalid token."""
        assert handler.verify_token("invalid.token.here") is False
    
    def test_custom_expiry(self, handler: JWTHandler):
        """Should respect custom expiry delta."""
        token = handler.create_access_token(
            "testuser",
            expires_delta=timedelta(hours=24),
        )
        
        payload = handler.decode_token(token)
        
        assert payload is not None
        # Token should still be valid after creation
        assert handler.verify_token(token) is True
    
    def test_different_secrets_produce_different_tokens(self):
        """Different secrets should produce different tokens."""
        handler1 = JWTHandler(
            secret_key="secret-key-one-that-is-at-least-32-characters",
            algorithm="HS256",
            expire_minutes=60,
        )
        handler2 = JWTHandler(
            secret_key="secret-key-two-that-is-at-least-32-characters",
            algorithm="HS256",
            expire_minutes=60,
        )
        
        token1 = handler1.create_access_token("testuser")
        token2 = handler2.create_access_token("testuser")
        
        assert token1 != token2
        
        # Token from handler1 should not be valid with handler2
        assert handler2.decode_token(token1) is None


class TestTokenPayload:
    """Tests for TokenPayload model."""
    
    def test_token_payload_creation(self):
        """Should create a valid token payload."""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        
        payload = TokenPayload(
            sub="testuser",
            exp=now,
            iat=now,
            type="access",
        )
        
        assert payload.sub == "testuser"
        assert payload.type == "access"
