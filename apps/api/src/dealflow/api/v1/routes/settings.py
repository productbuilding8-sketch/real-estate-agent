"""DAI-036: Tenant general settings endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.api.v1.schemas.settings import TenantSettingsResponse, UpdateTenantSettingsRequest
from dealflow.core.dependencies import require_permission
from dealflow.core.rbac import RequestContext
from dealflow.db.session import get_session
from dealflow.services.tenant_settings import TenantSettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get(
    "/general",
    response_model=TenantSettingsResponse,
    summary="Get tenant general settings",
)
async def get_general_settings(
    ctx: Annotated[RequestContext, Depends(require_permission("settings:read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantSettingsResponse:
    return await TenantSettingsService(session, ctx.tenant_id).get()


@router.patch(
    "/general",
    response_model=TenantSettingsResponse,
    summary="Update tenant general settings",
    responses={403: {"description": "Insufficient permissions"}},
)
async def update_general_settings(
    body: UpdateTenantSettingsRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("settings:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantSettingsResponse:
    return await TenantSettingsService(session, ctx.tenant_id).update(body)
