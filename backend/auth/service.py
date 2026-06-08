"""Authentication business logic — user verification and password hashing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt import JWTHandler
from backend.auth.schemas import TokenResponse, UserCreate
from backend.core.exceptions import AuthenticationException, NotFoundException
from backend.models.user import User



class AuthService:
    """Handles user authentication, registration, and token management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jwt = JWTHandler()

    # ── Password Utilities ───────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain-text password."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plain-text password against its hash."""
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


    # ── Authentication ───────────────────────────────────────────────────

    async def authenticate_user(self, email: str, password: str) -> TokenResponse:
        """Authenticate a user and return a JWT token pair.

        Raises:
            AuthenticationException: If credentials are invalid.
        """
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or not self.verify_password(password, user.hashed_password):
            raise AuthenticationException(detail="Invalid email or password.")

        if not user.is_active:
            raise AuthenticationException(detail="User account is deactivated.")

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self._session.flush()

        tokens = self._jwt.create_token_pair(
            subject=str(user.id),
            extra_claims={"email": user.email, "is_superuser": user.is_superuser},
        )
        return TokenResponse(**tokens)

    # ── Registration ─────────────────────────────────────────────────────

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user account."""
        user = User(
            email=data.email,
            hashed_password=self.hash_password(data.password),
            full_name=data.full_name,
            is_superuser=data.is_superuser,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    # ── Token Refresh ────────────────────────────────────────────────────

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Validate a refresh token and issue a new token pair.

        Raises:
            AuthenticationException: If the refresh token is invalid.
        """
        payload = self._jwt.decode_token(refresh_token)

        if payload.token_type != "refresh":
            raise AuthenticationException(detail="Invalid token type for refresh.")

        user = await self._session.get(User, payload.sub)
        if user is None or not user.is_active:
            raise AuthenticationException(detail="User not found or deactivated.")

        tokens = self._jwt.create_token_pair(
            subject=str(user.id),
            extra_claims={"email": user.email, "is_superuser": user.is_superuser},
        )
        return TokenResponse(**tokens)
