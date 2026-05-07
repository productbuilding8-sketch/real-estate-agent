"""DAI-026: Dashboard metrics endpoint."""

from __future__ import annotations

import uuid
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.dependencies import require_permission
from dealflow.core.rbac import RequestContext
from dealflow.db.models.audit_knowledge import ActivityTimeline
from dealflow.db.models.lead_ingestion import Lead
from dealflow.db.session import get_session

router = APIRouter(prefix="/metrics", tags=["metrics"])


class StatusCount(BaseModel):
    status: str
    count: int


class RecentEvent(BaseModel):
    lead_id: uuid.UUID
    event_type: str
    occurred_at: str


class DashboardMetrics(BaseModel):
    total_leads: int
    by_status: list[StatusCount]
    converted_count: int
    conversion_rate: float
    recent_events: list[RecentEvent]


@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Dashboard summary metrics",
)
async def get_dashboard_metrics(
    ctx: Annotated[RequestContext, Depends(require_permission("leads:read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardMetrics:
    tenant_id = ctx.tenant_id

    # Counts grouped by status
    status_q = (
        sa.select(Lead.status, sa.func.count(Lead.id).label("cnt"))
        .where(Lead.tenant_id == tenant_id)
        .group_by(Lead.status)
    )
    status_rows = (await session.execute(status_q)).all()

    by_status = [StatusCount(status=row.status, count=row.cnt) for row in status_rows]
    total_leads = sum(r.count for r in by_status)
    converted_count = next((r.count for r in by_status if r.status == "converted"), 0)
    conversion_rate = round(converted_count / total_leads, 4) if total_leads else 0.0

    # 10 most recent timeline events (agent-visible)
    events_q = (
        sa.select(ActivityTimeline)
        .where(
            ActivityTimeline.tenant_id == tenant_id,
            ActivityTimeline.visible_to_agent.is_(True),
        )
        .order_by(ActivityTimeline.occurred_at.desc())
        .limit(10)
    )
    event_rows = (await session.execute(events_q)).scalars().all()

    recent_events = [
        RecentEvent(
            lead_id=e.lead_id,
            event_type=e.event_type,
            occurred_at=e.occurred_at.isoformat(),
        )
        for e in event_rows
    ]

    return DashboardMetrics(
        total_leads=total_leads,
        by_status=by_status,
        converted_count=converted_count,
        conversion_rate=conversion_rate,
        recent_events=recent_events,
    )
