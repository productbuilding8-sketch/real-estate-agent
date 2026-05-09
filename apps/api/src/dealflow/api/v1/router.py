from fastapi import APIRouter

from dealflow.api.v1.routes import auth, health, integrations, leads, metrics, team, webhooks

api_router = APIRouter(prefix="/api/v1")

# System
api_router.include_router(health.router)

# Auth
api_router.include_router(auth.router)

# Leads
api_router.include_router(leads.router)

# Metrics / Dashboard
api_router.include_router(metrics.router)

# Webhooks (no auth — HMAC-protected)
api_router.include_router(webhooks.router)

# Integrations (CRM connections, sync triggers)
api_router.include_router(integrations.router)

# Team members
api_router.include_router(team.router)
