"""DAI-033/DAI-034: Team members + invitation management."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.dependencies import require_permission
from dealflow.core.rbac import RequestContext
from dealflow.db.models.tenant_auth import TenantInvitation, TenantMembership, User
from dealflow.db.session import get_session

router = APIRouter(prefix="/team", tags=["team"])

INVITATION_TTL_HOURS = 72


# ── Pydantic models ───────────────────────────────────────────────────────────


class TeamMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role_slug: str
    is_active: bool
    joined_at: datetime | None


class InviteRequest(BaseModel):
    email: str
    role_slug: str = "agent"


class ChangeRoleRequest(BaseModel):
    role_slug: str


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role_slug: str
    expires_at: datetime
    accepted_at: datetime | None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/members", response_model=list[TeamMember])
async def list_members(
    ctx: Annotated[RequestContext, Depends(require_permission("leads:read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[TeamMember]:
    rows = (
        (
            await session.execute(
                sa.select(
                    User.id,
                    User.name,
                    User.email,
                    TenantMembership.role_slug,
                    User.is_active,
                    TenantMembership.joined_at,
                )
                .join(TenantMembership, TenantMembership.user_id == User.id)
                .where(
                    TenantMembership.tenant_id == ctx.tenant_id,
                    TenantMembership.is_active.is_(True),
                    User.is_active.is_(True),
                )
                .order_by(User.name)
            )
        )
        .mappings()
        .all()
    )

    return [TeamMember(**dict(r)) for r in rows]


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_permission("team:manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    if user_id == ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "cannot_remove_self", "message": "You cannot remove yourself."},
        )
    result = await session.execute(
        sa.update(TenantMembership)
        .where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == ctx.tenant_id,
            TenantMembership.is_active.is_(True),
        )
        .values(is_active=False)
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Member not found."},
        )
    await session.commit()


@router.patch("/members/{user_id}/role", response_model=TeamMember)
async def change_member_role(
    user_id: uuid.UUID,
    body: ChangeRoleRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("team:manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TeamMember:
    result = await session.execute(
        sa.update(TenantMembership)
        .where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == ctx.tenant_id,
            TenantMembership.is_active.is_(True),
        )
        .values(role_slug=body.role_slug)
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Member not found."},
        )
    await session.commit()

    row = (
        (
            await session.execute(
                sa.select(
                    User.id,
                    User.name,
                    User.email,
                    TenantMembership.role_slug,
                    User.is_active,
                    TenantMembership.joined_at,
                )
                .join(TenantMembership, TenantMembership.user_id == User.id)
                .where(User.id == user_id, TenantMembership.tenant_id == ctx.tenant_id)
            )
        )
        .mappings()
        .one()
    )
    return TeamMember(**dict(row))


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    ctx: Annotated[RequestContext, Depends(require_permission("team:manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[InvitationResponse]:
    now = datetime.now(tz=UTC)
    rows = (
        (
            await session.execute(
                sa.select(TenantInvitation)
                .where(
                    TenantInvitation.tenant_id == ctx.tenant_id,
                    TenantInvitation.accepted_at.is_(None),
                    TenantInvitation.expires_at > now,
                )
                .order_by(TenantInvitation.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [InvitationResponse.model_validate(r) for r in rows]


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    body: InviteRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("team:manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvitationResponse:
    now = datetime.now(tz=UTC)
    expires_at = now + timedelta(hours=INVITATION_TTL_HOURS)
    token = secrets.token_urlsafe(32)

    invitation = TenantInvitation(
        tenant_id=ctx.tenant_id,
        email=body.email,
        role_slug=body.role_slug,
        invited_by_id=ctx.user_id,
        token=token,
        expires_at=expires_at,
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)
    return InvitationResponse.model_validate(invitation)


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(require_permission("team:manage"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    result = await session.execute(
        sa.delete(TenantInvitation).where(
            TenantInvitation.id == invitation_id,
            TenantInvitation.tenant_id == ctx.tenant_id,
        )
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Invitation not found."},
        )
    await session.commit()
