"""JWT token creation, verification, and refresh."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from pydantic import BaseModel

from backend.config.settings import get_settings
from backend.core.exceptions import AuthenticationException


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str
    exp: datetime
    iat: datetime
    token_type: str  # "access" | "refresh"
    jti: str | None = None


class JWTHandler:
    """Handles JWT token lifecycle — creation, decoding, and validation."""

    def __init__(self) -> None:
        settings = get_settings()
        self._secret_key = settings.jwt.secret_key.get_secret_value()
        self._algorithm = settings.jwt.algorithm
        self._access_expire_minutes = settings.jwt.access_token_expire_minutes
        self._refresh_expire_days = settings.jwt.refresh_token_expire_days

    def create_access_token(
        self,
        subject: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a short-lived access token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self._access_expire_minutes)

        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": expire,
            "token_type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, subject: str) -> str:
        """Create a long-lived refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self._refresh_expire_days)

        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": expire,
            "token_type": "refresh",
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT token.

        Raises:
            AuthenticationException: If the token is expired, malformed, or invalid.
        """
        try:
            raw = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return TokenPayload(**raw)
        except JWTError as exc:
            raise AuthenticationException(
                detail=f"Invalid or expired token: {exc}",
                error_code="INVALID_TOKEN",
            ) from exc

    def create_token_pair(
        self,
        subject: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Return both access and refresh tokens."""
        return {
            "access_token": self.create_access_token(subject, extra_claims),
            "refresh_token": self.create_refresh_token(subject),
            "token_type": "bearer",
        }
