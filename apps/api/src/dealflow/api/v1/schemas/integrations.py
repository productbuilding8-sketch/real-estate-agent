"""Schemas for the integrations API (DAI-031)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConnectRequest(BaseModel):
    provider: str
    access_token: str = Field(..., min_length=1)
    portal_id: str | None = None


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    last_sync_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_msg: str | None = None
    created_at: datetime | None = None


class TriggerSyncResponse(BaseModel):
    queued: bool
    job_id: str | None = None
    reason: str | None = None
