from fastapi import APIRouter

from dealflow.api.v1.routes import auth, health

api_router = APIRouter(prefix="/api/v1")

# System
api_router.include_router(health.router)

# Auth
api_router.include_router(auth.router)
