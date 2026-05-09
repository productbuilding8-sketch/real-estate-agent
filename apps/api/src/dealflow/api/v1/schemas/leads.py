"""Response schemas for the leads API (DAI-018/019/021/022)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None


class SourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str


class LeadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    lead_type: str
    confidence_score: float | None = None
    assigned_agent_id: uuid.UUID | None = None
    assigned_agent_name: str | None = None
    created_at: datetime
    last_activity_at: datetime | None = None
    contact: ContactSummary
    source: SourceSummary


class LeadListResponse(BaseModel):
    items: list[LeadListItem]
    total: int
    page: int
    pages: int


class ContactPointSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    value: str
    is_primary: bool


class ContactDetail(ContactSummary):
    contact_points: list[ContactPointSchema] = []


class LeadPreferenceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_min: float | None = None
    budget_max: float | None = None
    location_city: str | None = None
    location_state: str | None = None
    property_types: list[str] | None = None
    timeline: str | None = None
    financing_status: str | None = None
    purpose: str | None = None
    appointment_preferred: bool | None = None


class TimelineEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    event_data: dict[str, Any] | None = None
    actor_type: str
    occurred_at: datetime


class LeadDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    lead_type: str
    confidence_score: float | None = None
    assigned_agent_id: uuid.UUID | None = None
    created_at: datetime
    last_activity_at: datetime | None = None
    first_response_at: datetime | None = None
    stale_at: datetime | None = None
    raw_payload: dict[str, Any] | None = None
    contact: ContactDetail
    source: SourceSummary
    preferences: LeadPreferenceSchema | None = None
    timeline: list[TimelineEventSchema] = []


# ── Mutation request / response schemas (DAI-021) ────────────────────────────


class UpdateStatusRequest(BaseModel):
    status: str
    reason: str | None = None


class AssignRequest(BaseModel):
    agent_id: uuid.UUID | None = None


class LeadStatusResponse(BaseModel):
    id: uuid.UUID
    status: str


class LeadAssignResponse(BaseModel):
    id: uuid.UUID
    assigned_agent_id: uuid.UUID | None


class AddNoteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class SendSmsRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1600)


class SendSmsResponse(BaseModel):
    queued: bool
    job_id: str | None = None


class SendEmailRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)


class SendEmailResponse(BaseModel):
    queued: bool
    job_id: str | None = None
