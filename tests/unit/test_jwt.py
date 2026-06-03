"""Unit tests for JWTHandler token operations."""

from __future__ import annotations

import pytest
from jose import jwt

from backend.auth.jwt import JWTHandler, TokenPayload
from backend.core.exceptions import AuthenticationException


def test_create_and_decode_access_token() -> None:
    """Test that a generated access token is successfully decoded and contains correct payload claims."""
    handler = JWTHandler()
    subject = "user123"
    claims = {"role": "admin"}

    token = handler.create_access_token(subject, extra_claims=claims)
    payload = handler.decode_token(token)

    assert isinstance(payload, TokenPayload)
    assert payload.sub == subject
    assert payload.token_type == "access"


def test_create_and_decode_refresh_token() -> None:
    """Test that a generated refresh token is successfully decoded and verified."""
    handler = JWTHandler()
    subject = "user123"

    token = handler.create_refresh_token(subject)
    payload = handler.decode_token(token)

    assert isinstance(payload, TokenPayload)
    assert payload.sub == subject
    assert payload.token_type == "refresh"


def test_decode_invalid_token() -> None:
    """Test that decoding an invalid token raises AuthenticationException."""
    handler = JWTHandler()
    invalid_token = "invalid.token.string"

    with pytest.raises(AuthenticationException):
        handler.decode_token(invalid_token)


def test_token_pair_generation() -> None:
    """Test token pair contains both access and refresh tokens."""
    handler = JWTHandler()
    subject = "user456"

    pair = handler.create_token_pair(subject)
    assert "access_token" in pair
    assert "refresh_token" in pair
    assert pair["token_type"] == "bearer"
