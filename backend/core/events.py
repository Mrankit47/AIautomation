"""FastAPI application lifecycle events (startup / shutdown)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from backend.config.settings import get_settings
from backend.core.logging import get_logger, setup_logging
from backend.database.session import async_engine, dispose_engine, init_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown resources."""
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging(
        log_level=settings.app_log_level,
        json_format=settings.app_log_json,
    )
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
    )

    # Initialize database engine
    init_engine(settings.postgres)
    logger.info("database_engine_initialized")

    # Initialize Redis connection pool
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.redis.url,
        max_connections=50,
        decode_responses=True,
    )
    app.state.redis = aioredis.Redis(connection_pool=redis_pool)
    logger.info("redis_pool_initialized")

    logger.info("application_started")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("application_shutting_down")

    # Close Redis
    await app.state.redis.aclose()
    await redis_pool.aclose()
    logger.info("redis_pool_closed")

    # Dispose database engine
    await dispose_engine()
    logger.info("database_engine_disposed")

    logger.info("application_stopped")
