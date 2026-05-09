"""DAI-018/019/021: Lead list, detail, and mutation endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.api.v1.schemas.leads import (
    AddNoteRequest,
    AssignRequest,
    LeadAssignResponse,
    LeadDetail,
    LeadListResponse,
    LeadStatusResponse,
    SendEmailRequest,
    SendEmailResponse,
    SendSmsRequest,
    SendSmsResponse,
    TimelineEventSchema,
    UpdateStatusRequest,
)
from dealflow.core.dependencies import require_permission
from dealflow.core.errors import AppError
from dealflow.core.queue import get_job_queue
from dealflow.core.rbac import RequestContext
from dealflow.db.session import get_session
from dealflow.services.lead_mutations import LeadMutationService
from dealflow.services.leads import LeadService
from dealflow.services.timeline import TimelineService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get(
    "",
    response_model=LeadListResponse,
    summary="List leads with optional filters",
    responses={
        403: {"description": "Insufficient permissions"},
    },
)
async def list_leads(
    ctx: Annotated[RequestContext, Depends(require_permission("leads:read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: str | None = Query(None, alias="status", description="Filter by lead status"),
    search: str | None = Query(None, description="Search by contact name"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
) -> LeadListResponse:
    service = LeadService(session, ctx.tenant_id)
    items, total = await service.list(status=status_filter, search=search, page=page, limit=limit)
    counts = await service.status_counts(search=search)
    pages = max(1, (total + limit - 1) // limit)
    return LeadListResponse(items=items, total=total, page=page, pages=pages, status_counts=counts)


@router.get(
    "/{lead_id}",
    response_model=LeadDetail,
    summary="Get full lead detail",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Lead not found"},
    },
)
async def get_lead(
    lead_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_permission("leads:read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadDetail:
    service = LeadService(session, ctx.tenant_id)
    lead = await service.get_detail(lead_id)
    if lead is None:
        raise AppError("lead_not_found", "Lead not found", 404)
    return lead


@router.patch(
    "/{lead_id}/status",
    response_model=LeadStatusResponse,
    summary="Transition a lead to a new status",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Lead not found"},
        409: {"description": "Invalid status transition"},
        422: {"description": "Unrecognised status value"},
    },
)
async def update_lead_status(
    lead_id: uuid.UUID,
    body: UpdateStatusRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("leads:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadStatusResponse:
    service = LeadMutationService(session, ctx.tenant_id, ctx.user_id)
    lead = await service.update_status(lead_id, body.status, body.reason)
    return LeadStatusResponse(id=lead.id, status=lead.status)


@router.patch(
    "/{lead_id}/assign",
    response_model=LeadAssignResponse,
    summary="Assign or unassign a lead to an agent",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Lead not found"},
    },
)
async def assign_lead(
    lead_id: uuid.UUID,
    body: AssignRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("leads:assign"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadAssignResponse:
    service = LeadMutationService(session, ctx.tenant_id, ctx.user_id)
    lead = await service.assign(lead_id, body.agent_id)
    return LeadAssignResponse(id=lead.id, assigned_agent_id=lead.assigned_agent_id)


@router.post(
    "/{lead_id}/notes",
    response_model=TimelineEventSchema,
    status_code=201,
    summary="Add a note to a lead's activity timeline",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Lead not found"},
    },
)
async def add_lead_note(
    lead_id: uuid.UUID,
    body: AddNoteRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("leads:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TimelineEventSchema:
    service = TimelineService(session, ctx.tenant_id, actor_id=ctx.user_id, actor_type="user")
    entry = await service.add_note(lead_id, body.text)
    return TimelineEventSchema.model_validate(entry)


@router.post(
    "/{lead_id}/sms",
    response_model=SendSmsResponse,
    status_code=202,
    summary="Enqueue an outbound SMS to a lead",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Lead not found"},
    },
)
async def send_lead_sms(
    lead_id: uuid.UUID,
    body: SendSmsRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("leads:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[ArqRedis | None, Depends(get_job_queue)] = None,
) -> SendSmsResponse:
    service = LeadService(session, ctx.tenant_id)
    lead = await service.get_detail(lead_id)
    if lead is None:
        raise AppError("lead_not_found", "Lead not found", 404)

    if queue is None:
        return SendSmsResponse(queued=False)

    job = await queue.enqueue_job(
        "send_sms_job",
        lead_id=str(lead_id),
        tenant_id=str(ctx.tenant_id),
        message=body.message,
    )
    return SendSmsResponse(queued=True, job_id=job.job_id if job else None)


@router.post(
    "/{lead_id}/email",
    response_model=SendEmailResponse,
    status_code=202,
    summary="Enqueue an outbound email to a lead",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Lead not found"},
    },
)
async def send_lead_email(
    lead_id: uuid.UUID,
    body: SendEmailRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("leads:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[ArqRedis | None, Depends(get_job_queue)] = None,
) -> SendEmailResponse:
    service = LeadService(session, ctx.tenant_id)
    lead = await service.get_detail(lead_id)
    if lead is None:
        raise AppError("lead_not_found", "Lead not found", 404)

    if queue is None:
        return SendEmailResponse(queued=False)

    job = await queue.enqueue_job(
        "send_email_job",
        lead_id=str(lead_id),
        tenant_id=str(ctx.tenant_id),
        subject=body.subject,
        body=body.body,
    )
    return SendEmailResponse(queued=True, job_id=job.job_id if job else None)
