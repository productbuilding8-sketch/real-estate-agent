"""DAI-018/019/021: Lead list, detail, and mutation endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.api.v1.schemas.leads import (
    AssignRequest,
    LeadAssignResponse,
    LeadDetail,
    LeadListResponse,
    LeadStatusResponse,
    UpdateStatusRequest,
)
from dealflow.core.dependencies import require_permission
from dealflow.core.errors import AppError
from dealflow.core.rbac import RequestContext
from dealflow.db.session import get_session
from dealflow.services.lead_mutations import LeadMutationService
from dealflow.services.leads import LeadService

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
    items, total = await service.list(
        status=status_filter,
        search=search,
        page=page,
        limit=limit,
    )
    pages = max(1, (total + limit - 1) // limit)
    return LeadListResponse(items=items, total=total, page=page, pages=pages)


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
