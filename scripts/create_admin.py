#!/usr/bin/env python
"""Bootstrap the first superuser when the users table is empty.

Usage:
    python -m scripts.create_admin

This script will ONLY create a user when the users table has zero rows.
Once any user exists, it refuses to proceed — use the /api/v1/auth/register
endpoint with superuser credentials instead.
"""

from __future__ import annotations

import asyncio
import sys

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config.settings import get_settings
from backend.models.user import User


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt — compatible with passlib's $2b$ scheme."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def create_first_superuser(
    email: str,
    password: str,
    full_name: str | None = None,
) -> None:
    """Insert the first superuser if and only if no users exist."""
    settings = get_settings()
    engine = create_async_engine(settings.postgres.async_url, echo=False)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        # ── Safety gate: refuse if any user exists ──────────────────────
        count_result = await session.execute(select(func.count()).select_from(User))
        user_count = count_result.scalar_one()

        if user_count > 0:
            print(f"✘ Aborted — {user_count} user(s) already exist.")
            print("  Use the /api/v1/auth/register endpoint instead.")
            await engine.dispose()
            sys.exit(1)

        # ── Create the superuser ────────────────────────────────────────
        hashed = _hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print("✔ First superuser created successfully.")
        print(f"  ID    : {user.id}")
        print(f"  Email : {user.email}")
        print(f"  Active: {user.is_active}")
        print(f"  Super : {user.is_superuser}")

    await engine.dispose()


if __name__ == "__main__":
    # Default bootstrap credentials — override via env or edit here.
    asyncio.run(
        create_first_superuser(
            email="admin@example.com",
            password="Admin@123456",
            full_name="Admin",
        )
    )
