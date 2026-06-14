"""Top-level API router aggregating all v1 sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.v1.artwork import router as artwork_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.health import router as health_router
from backend.api.v1.dashboard import router as dashboard_router
from backend.api.v1.system import router as system_router
from backend.api.v1.ingestion import router as ingestion_router
from backend.api.v1.workflow import router as workflow_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(artwork_router)
api_router.include_router(dashboard_router)
api_router.include_router(system_router)
api_router.include_router(ingestion_router)
api_router.include_router(workflow_router)
