"""Authentication API endpoints — login, refresh, register."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_superuser
from backend.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from backend.auth.service import AuthService
from backend.database.session import get_db_session
from backend.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuthService:
    return AuthService(session=session)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Authenticate and return JWT token pair."""
    return await auth_service.authenticate_user(
        email=body.email, password=body.password
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    auth_service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Refresh access token using a valid refresh token."""
    return await auth_service.refresh_tokens(body.refresh_token)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserCreate,
    auth_service: AuthService = Depends(_get_auth_service),
    admin: User = Depends(require_superuser),
) -> UserResponse:
    """Register a new user (superuser only)."""
    user = await auth_service.create_user(body)
    return UserResponse.model_validate(user)
