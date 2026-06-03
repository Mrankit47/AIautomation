"""Auth Pydantic schemas for requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials for user login."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """JWT token pair returned on successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Payload for refreshing an access token."""

    refresh_token: str


class UserCreate(BaseModel):
    """Payload for creating a new user (admin only)."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    is_superuser: bool = False


class UserResponse(BaseModel):
    """Public user representation."""

    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}
