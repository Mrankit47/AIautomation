"""Top-level API router aggregating all v1 sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.v1.artwork import router as artwork_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.health import router as health_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(artwork_router)
