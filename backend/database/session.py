"""Async SQLAlchemy engine and session factory.

The engine is initialised once at application startup via ``init_engine``
and disposed on shutdown via ``dispose_engine``.  Sessions are obtained
through the ``get_db_session`` async generator for FastAPI dependency injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from backend.config.settings import get_settings

# Module-level references for sync engine
_sync_engine = None
_SyncSessionLocal: sessionmaker | None = None


def get_sync_session() -> Session:
    """Create a sync database session using psycopg2."""
    global _sync_engine, _SyncSessionLocal  # noqa: PLW0603

    if _SyncSessionLocal is None:
        settings = get_settings()
        _sync_engine = create_engine(
            settings.postgres.sync_url,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            echo=False,
        )
        _SyncSessionLocal = sessionmaker(
            bind=_sync_engine,
            class_=Session,
            expire_on_commit=False,
        )
    return _SyncSessionLocal()

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine

    from backend.config.settings import DatabaseSettings

# Module-level references set by init_engine()
async_engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(db_settings: DatabaseSettings) -> None:
    """Create the async engine and session factory.

    Must be called once during application startup (see ``lifespan``).
    """
    global async_engine, AsyncSessionLocal  # noqa: PLW0603

    async_engine = create_async_engine(
        db_settings.async_url,
        pool_size=db_settings.pool_size,
        max_overflow=db_settings.max_overflow,
        pool_pre_ping=True,
        echo=False,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def dispose_engine() -> None:
    """Dispose the async engine.  Call during application shutdown."""
    global async_engine  # noqa: PLW0603

    if async_engine is not None:
        await async_engine.dispose()
        async_engine = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    if AsyncSessionLocal is None:
        msg = "Database engine not initialised. Call init_engine() first."
        raise RuntimeError(msg)

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
