"""Auth routes: identity probe + first-login user/membership registration (DAI-035/DAI-038)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.auth import TokenPayload
from dealflow.core.dependencies import get_current_user, get_tenant_id
from dealflow.db.models.tenant_auth import TenantMembership, User
from dealflow.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    sub: str
    email: str | None = None
    name: str | None = None


class RegisterResponse(BaseModel):
    user_id: str
    auth0_sub: str
    email: str
    name: str
    role_slug: str
    tenant_id: str


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Current user identity",
    responses={401: {"description": "Missing or invalid token"}},
)
async def me(current_user: TokenPayload = Depends(get_current_user)) -> MeResponse:
    return MeResponse(sub=current_user.sub, email=current_user.email, name=current_user.name)


@router.post(
    "/register",
    response_model=RegisterResponse,
    summary="Upsert user + tenant membership on first login",
    responses={
        200: {"description": "User registered or already exists"},
        401: {"description": "Missing or invalid token"},
    },
)
async def register(
    token: Annotated[TokenPayload, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RegisterResponse:
    now = datetime.now(tz=UTC)

    # Upsert User — update profile fields on conflict but never deactivate.
    user_stmt = (
        pg_insert(User)
        .values(
            id=uuid.uuid4(),
            auth0_sub=token.sub,
            email=token.email or "",
            name=token.name or token.sub,
            is_active=True,
            last_seen_at=now,
        )
        .on_conflict_do_update(
            index_elements=["auth0_sub"],
            set_={
                "email": token.email or "",
                "name": token.name or token.sub,
                "last_seen_at": now,
                "updated_at": now,
            },
        )
        .returning(User.id)
    )
    user_id: uuid.UUID = (await session.execute(user_stmt)).scalar_one()

    # First active member in this tenant becomes owner_admin; subsequent users get agent.
    other_count: int = (
        await session.execute(
            sa.select(sa.func.count(TenantMembership.id)).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.is_active.is_(True),
                TenantMembership.user_id != user_id,
            )
        )
    ).scalar_one()
    default_role = "owner_admin" if other_count == 0 else "agent"

    # Upsert TenantMembership — never downgrade an existing role.
    membership_stmt = (
        pg_insert(TenantMembership)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            role_slug=default_role,
            is_active=True,
            joined_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_tenant_memberships_user_tenant",
            set_={
                "is_active": True,
                "updated_at": now,
            },
        )
        .returning(TenantMembership.role_slug)
    )
    role_slug: str = (await session.execute(membership_stmt)).scalar_one()

    await session.commit()

    return RegisterResponse(
        user_id=str(user_id),
        auth0_sub=token.sub,
        email=token.email or "",
        name=token.name or token.sub,
        role_slug=role_slug,
        tenant_id=str(tenant_id),
    )
