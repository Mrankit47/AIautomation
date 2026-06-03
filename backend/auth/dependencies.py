"""FastAPI authentication dependencies for route protection."""

from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt import JWTHandler
from backend.core.exceptions import AuthenticationException, AuthorizationException
from backend.database.session import get_db_session
from backend.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Decode the Bearer token and return the corresponding active user.

    Raises:
        AuthenticationException: If the token is invalid or user not found.
    """
    jwt_handler = JWTHandler()
    payload = jwt_handler.decode_token(token)

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError as exc:
        raise AuthenticationException(detail="Invalid token subject.") from exc

    user = await session.get(User, user_id)
    if user is None:
        raise AuthenticationException(detail="User not found.")
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user is active.

    Raises:
        AuthenticationException: If the user account is deactivated.
    """
    if not user.is_active:
        raise AuthenticationException(detail="User account is deactivated.")
    return user


async def require_superuser(
    user: User = Depends(get_current_active_user),
) -> User:
    """Ensure the authenticated user has superuser privileges.

    Raises:
        AuthorizationException: If the user is not a superuser.
    """
    if not user.is_superuser:
        raise AuthorizationException(detail="Superuser privileges required.")
    return user
