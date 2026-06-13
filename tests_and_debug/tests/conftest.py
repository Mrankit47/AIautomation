"""Shared pytest fixtures for unit and integration testing."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db_session, get_redis
from backend.config.settings import Settings, get_settings
from backend.main import create_app


# ── Mock Settings ──────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Return a test-specific settings instance."""
    settings = get_settings()
    settings.app_env = "testing"
    settings.app_debug = True
    settings.jwt.secret_key = "test-secret-key-test-secret-key-test-secret-key-test-secret-key"
    return settings


# ── Database Mocking ───────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def mock_db_session() -> AsyncSession:
    """Provide a mock async SQLAlchemy database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


# ── Redis Mocking ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_redis() -> MagicMock:
    """Provide a mock Redis client."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.ping = AsyncMock(return_value=True)
    return client


# ── App & Client Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def app(mock_db_session: AsyncSession, mock_redis: MagicMock) -> FastAPI:
    """Create a test FastAPI instance with overridden dependencies."""
    test_app = create_app()

    # Override database session dependency
    test_app.dependency_overrides[get_db_session] = lambda: mock_db_session

    # Override Redis dependency
    test_app.dependency_overrides[get_redis] = lambda: mock_redis

    # Inject mock Redis into app state
    test_app.state.redis = mock_redis

    yield test_app
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Provide an async HTTP client for API requests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Celery Mocking ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_celery(monkeypatch) -> MagicMock:
    """Automatically mock Celery tasks to prevent real worker calls during tests."""
    mock_app = MagicMock()
    mock_app.send_task = MagicMock()

    # Mock the Celery tasks dispatch functions
    from backend.tasks.artwork_task import process_artwork
    from backend.tasks.workflow_task import execute_workflow

    # Mock the delay method on tasks
    monkeypatch.setattr(process_artwork, "delay", MagicMock(return_value=MagicMock(id="mock-task-id")))
    monkeypatch.setattr(execute_workflow, "delay", MagicMock(return_value=MagicMock(id="mock-task-id")))

    return mock_app
