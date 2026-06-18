"""Pydantic schemas for health-check endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Basic liveness probe response."""

    status: str = "healthy"
    app_name: str
    version: str = "0.1.0"


class ServiceStatus(BaseModel):
    """Health status of an individual service dependency."""

    name: str
    status: str  # "healthy" | "unhealthy"
    latency_ms: float | None = None
    detail: str | None = None


class HealthReadyResponse(BaseModel):
    """Readiness probe response with dependency checks."""

    status: str  # "ready" | "degraded" | "unhealthy"
    services: list[ServiceStatus]


class IntegrationStatus(BaseModel):
    """Health status of an individual integration."""

    name: str
    status: str  # "healthy" | "unhealthy" | "disabled"
    detail: str | None = None


class IntegrationsHealthResponse(BaseModel):
    """Overall integrations health check response."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    integrations: list[IntegrationStatus]

