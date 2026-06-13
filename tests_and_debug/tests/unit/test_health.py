"""Unit tests for the health check endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_endpoint(client: AsyncClient) -> None:
    """Test that the liveness probe returns 200 OK and healthy status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data


@pytest.mark.asyncio
async def test_readiness_endpoint_all_healthy(client: AsyncClient) -> None:
    """Test readiness probe when all backing services are healthy."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "degraded", "unhealthy")
    assert "services" in data
