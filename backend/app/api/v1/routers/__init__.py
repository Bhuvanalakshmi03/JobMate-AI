"""API v1 router registry."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers.health import router as health_router
from app.modules.authentication.router import router as auth_router
from app.modules.profile.router import router as profile_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(profile_router)
