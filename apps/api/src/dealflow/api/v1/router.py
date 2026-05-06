from fastapi import APIRouter

from dealflow.api.v1.routes import auth, health, leads, webhooks

api_router = APIRouter(prefix="/api/v1")

# System
api_router.include_router(health.router)

# Auth
api_router.include_router(auth.router)

# Leads
api_router.include_router(leads.router)

# Webhooks (no auth — HMAC-protected)
api_router.include_router(webhooks.router)
