"""DAI-036: Service for reading and updating tenant-level settings."""

from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.api.v1.schemas.settings import (
    NotificationPreferences,
    TenantSettingsResponse,
    UpdateTenantSettingsRequest,
)
from dealflow.core.errors import AppError
from dealflow.db.models.tenant_auth import Tenant

_DEFAULT_NOTIFICATIONS: dict[str, Any] = {
    "new_lead_email": True,
    "lead_assigned_email": True,
    "daily_summary": False,
    "weekly_report": False,
}


class TenantSettingsService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def _get_tenant(self) -> Tenant:
        result = await self._session.execute(sa.select(Tenant).where(Tenant.id == self._tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise AppError("tenant_not_found", "Tenant not found", 404)
        return tenant

    async def get(self) -> TenantSettingsResponse:
        tenant = await self._get_tenant()
        stored = (tenant.settings or {}).get("notifications", {})
        notif = {**_DEFAULT_NOTIFICATIONS, **stored}
        return TenantSettingsResponse(
            name=tenant.name,
            slug=tenant.slug,
            timezone=tenant.timezone,
            notifications=NotificationPreferences(**notif),
        )

    async def update(self, req: UpdateTenantSettingsRequest) -> TenantSettingsResponse:
        tenant = await self._get_tenant()

        if req.name is not None:
            tenant.name = req.name
        if req.timezone is not None:
            tenant.timezone = req.timezone
        if req.notifications is not None:
            current_settings: dict[str, Any] = dict(tenant.settings or {})
            current_settings["notifications"] = req.notifications.model_dump()
            tenant.settings = current_settings

        await self._session.commit()
        await self._session.refresh(tenant)

        stored = (tenant.settings or {}).get("notifications", {})
        notif = {**_DEFAULT_NOTIFICATIONS, **stored}
        return TenantSettingsResponse(
            name=tenant.name,
            slug=tenant.slug,
            timezone=tenant.timezone,
            notifications=NotificationPreferences(**notif),
        )
