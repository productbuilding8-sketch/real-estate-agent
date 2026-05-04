"""DAI-012: Role-based access control — permission checking and request context resolution."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.db.models.tenant_auth import Role, TenantMembership, User

# Roles are seeded once in migration 0001 and never mutated at runtime.
# Cache avoids a DB round-trip on every request.
_ROLE_CACHE: dict[str, list[str]] = {}


def clear_role_cache() -> None:
    """Clear the role permission cache — call in test teardown."""
    _ROLE_CACHE.clear()


def check_permission(granted: list[str], required: str) -> bool:
    """Return True if `required` is covered by any pattern in `granted`.

    Supports fnmatch globs: "*" covers everything, "leads:*" covers any leads
    permission, "leads:read" is an exact match.
    """
    for g in granted:
        if g == "*" or fnmatch(required, g):
            return True
    return False


@dataclass(frozen=True)
class RequestContext:
    user_id: uuid.UUID
    auth0_sub: str
    tenant_id: uuid.UUID
    role_slug: str
    permissions: list[str]

    def has_permission(self, required: str) -> bool:
        return check_permission(self.permissions, required)


async def _load_role_permissions(role_slug: str, session: AsyncSession) -> list[str]:
    if role_slug in _ROLE_CACHE:
        return _ROLE_CACHE[role_slug]

    result = await session.execute(sa.select(Role).where(Role.slug == role_slug))
    role = result.scalar_one_or_none()
    permissions: list[str] = role.permissions if role and role.permissions else []
    _ROLE_CACHE[role_slug] = permissions
    return permissions


async def resolve_context(
    auth0_sub: str,
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> RequestContext:
    """Build a RequestContext for the authenticated user in the given tenant.

    Raises ValueError for unknown user, non-member, expired/inactive membership.
    """
    user_result = await session.execute(
        sa.select(User).where(User.auth0_sub == auth0_sub, User.is_active.is_(True))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise ValueError("user_not_found")

    membership_result = await session.execute(
        sa.select(TenantMembership).where(
            TenantMembership.user_id == user.id,
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.is_active.is_(True),
        )
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise ValueError("not_a_member")

    if membership.expires_at is not None:
        now = datetime.now(tz=timezone.utc)
        if membership.expires_at.replace(tzinfo=timezone.utc) < now:
            raise ValueError("membership_expired")

    permissions = await _load_role_permissions(membership.role_slug, session)

    return RequestContext(
        user_id=user.id,
        auth0_sub=auth0_sub,
        tenant_id=tenant_id,
        role_slug=membership.role_slug,
        permissions=permissions,
    )
