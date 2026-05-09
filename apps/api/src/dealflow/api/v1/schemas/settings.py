"""Schemas for the tenant settings API (DAI-036)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NotificationPreferences(BaseModel):
    new_lead_email: bool = True
    lead_assigned_email: bool = True
    daily_summary: bool = False
    weekly_report: bool = False


class TenantSettingsResponse(BaseModel):
    name: str
    slug: str
    timezone: str
    notifications: NotificationPreferences


class UpdateTenantSettingsRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    timezone: str | None = Field(None, min_length=1, max_length=100)
    notifications: NotificationPreferences | None = None
