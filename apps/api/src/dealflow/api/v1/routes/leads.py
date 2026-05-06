"""DAI-018/019: Lead list and detail endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.api.v1.schemas.leads import LeadDetail, LeadListResponse
from dealflow.core.dependencies import require_permission
from dealflow.core.errors import AppError
from dealflow.core.rbac import RequestContext
from dealflow.db.session import get_session
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
