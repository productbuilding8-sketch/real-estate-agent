"""DAI-033: Team members endpoint — list users in a tenant for lead assignment."""

from __future__ import annotations

import uuid
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.dependencies import require_permission
from dealflow.core.rbac import RequestContext
from dealflow.db.models.tenant_auth import TenantMembership, User
from dealflow.db.session import get_session

router = APIRouter(prefix="/team", tags=["team"])


class TeamMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role_slug: str
    is_active: bool


@router.get(
    "/members",
    response_model=list[TeamMember],
    summary="List active team members for this tenant",
)
async def list_members(
    ctx: Annotated[RequestContext, Depends(require_permission("leads:read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[TeamMember]:
    rows = (
        await session.execute(
            sa.select(User.id, User.name, User.email, TenantMembership.role_slug, User.is_active)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == ctx.tenant_id,
                TenantMembership.is_active.is_(True),
                User.is_active.is_(True),
            )
            .order_by(User.name)
        )
    ).mappings().all()

    return [
        TeamMember(
            id=r["id"],
            name=r["name"],
            email=r["email"],
            role_slug=r["role_slug"],
            is_active=r["is_active"],
        )
        for r in rows
    ]
