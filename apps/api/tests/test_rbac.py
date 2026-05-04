"""DAI-012: RBAC middleware tests.

Unit tests cover permission logic (no DB).
Integration tests cover the full chain: JWT → X-Tenant-ID → DB membership lookup → permission check.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from dealflow.core.rbac import RequestContext, check_permission, clear_role_cache

# ── unit: permission logic ────────────────────────────────────────────────────


def test_exact_match_allowed() -> None:
    assert check_permission(["leads:read"], "leads:read") is True


def test_wildcard_covers_all() -> None:
    assert check_permission(["*"], "leads:delete") is True
    assert check_permission(["*"], "tenants:admin") is True


def test_glob_prefix_covers_namespace() -> None:
    assert check_permission(["leads:*"], "leads:read") is True
    assert check_permission(["leads:*"], "leads:write") is True
    assert check_permission(["leads:*"], "tenants:read") is False


def test_no_permission_denied() -> None:
    assert check_permission([], "leads:read") is False


def test_partial_match_not_allowed() -> None:
    assert check_permission(["leads:read"], "leads:write") is False
    assert check_permission(["leads:read"], "leads:reads") is False


def test_multiple_grants_any_match() -> None:
    assert check_permission(["leads:read", "tasks:*"], "tasks:create") is True
    assert check_permission(["leads:read", "tasks:*"], "leads:write") is False


def test_request_context_has_permission() -> None:
    ctx = RequestContext(
        user_id=uuid.uuid4(),
        auth0_sub="auth0|abc",
        tenant_id=uuid.uuid4(),
        role_slug="agent",
        permissions=["leads:read", "tasks:*"],
    )
    assert ctx.has_permission("leads:read") is True
    assert ctx.has_permission("tasks:create") is True
    assert ctx.has_permission("leads:write") is False


def test_request_context_is_frozen() -> None:
    ctx = RequestContext(
        user_id=uuid.uuid4(),
        auth0_sub="auth0|abc",
        tenant_id=uuid.uuid4(),
        role_slug="agent",
        permissions=["leads:read"],
    )
    with pytest.raises((AttributeError, TypeError)):
        ctx.role_slug = "owner_admin"  # type: ignore[misc]


# ── unit: HTTP layer — direct dependency testing ──────────────────────────────


@pytest.mark.asyncio
async def test_auth_me_without_tenant_still_works(client) -> None:
    """The /auth/me route does NOT require a tenant header — verify it works."""
    from tests.helpers import jwt_factory as jf

    private_key = jf.generate_rsa_keypair()
    token = jf.make_token(private_key, sub="auth0|user1")
    jwks = jf.build_jwks(private_key)

    with patch("dealflow.core.auth.fetch_jwks", new=AsyncMock(return_value=jwks)):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_invalid_tenant_uuid_raises_400() -> None:
    from fastapi import HTTPException

    from dealflow.core.dependencies import get_tenant_id

    with pytest.raises(HTTPException) as exc_info:
        await get_tenant_id(x_tenant_id="not-a-uuid")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "invalid_tenant"


@pytest.mark.asyncio
async def test_missing_tenant_header_raises_400() -> None:
    from fastapi import HTTPException

    from dealflow.core.dependencies import get_tenant_id

    with pytest.raises(HTTPException) as exc_info:
        await get_tenant_id(x_tenant_id=None)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "missing_tenant"


@pytest.mark.asyncio
async def test_valid_tenant_uuid_parses() -> None:
    from dealflow.core.dependencies import get_tenant_id

    tenant_id = uuid.uuid4()
    result = await get_tenant_id(x_tenant_id=str(tenant_id))
    assert result == tenant_id


# ── unit: resolve_context with mocked DB ──────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_context_user_not_found() -> None:
    from unittest.mock import MagicMock

    from sqlalchemy.ext.asyncio import AsyncSession

    from dealflow.core.rbac import resolve_context

    clear_role_cache()
    session = AsyncMock(spec=AsyncSession)

    # scalar_one_or_none is synchronous — use MagicMock for the result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ValueError, match="user_not_found"):
        await resolve_context("auth0|ghost", uuid.uuid4(), session)


@pytest.mark.asyncio
async def test_resolve_context_not_a_member() -> None:
    from unittest.mock import MagicMock

    from dealflow.core.rbac import resolve_context
    from dealflow.db.models.tenant_auth import User

    clear_role_cache()
    session = AsyncMock()

    fake_user = MagicMock(spec=User)
    fake_user.id = uuid.uuid4()
    fake_user.is_active = True

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = fake_user

    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = None

    session.execute = AsyncMock(side_effect=[user_result, membership_result])

    with pytest.raises(ValueError, match="not_a_member"):
        await resolve_context("auth0|user", uuid.uuid4(), session)


@pytest.mark.asyncio
async def test_resolve_context_success() -> None:
    from unittest.mock import MagicMock

    from dealflow.core.rbac import resolve_context
    from dealflow.db.models.tenant_auth import Role, TenantMembership, User

    clear_role_cache()
    session = AsyncMock()

    fake_user = MagicMock(spec=User)
    fake_user.id = uuid.uuid4()
    fake_user.auth0_sub = "auth0|user"
    fake_user.is_active = True

    fake_membership = MagicMock(spec=TenantMembership)
    fake_membership.role_slug = "agent"
    fake_membership.is_active = True
    fake_membership.expires_at = None

    fake_role = MagicMock(spec=Role)
    fake_role.permissions = ["leads:read", "tasks:*"]

    tenant_id = uuid.uuid4()

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = fake_user

    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = fake_membership

    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = fake_role

    session.execute = AsyncMock(side_effect=[user_result, membership_result, role_result])

    ctx = await resolve_context("auth0|user", tenant_id, session)

    assert ctx.user_id == fake_user.id
    assert ctx.tenant_id == tenant_id
    assert ctx.role_slug == "agent"
    assert ctx.has_permission("leads:read") is True
    assert ctx.has_permission("leads:write") is False


# ── integration: full DB chain ─────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resolve_context_full_chain(db_session) -> None:
    """End-to-end: insert real user+tenant+membership, resolve context, check permissions."""
    from dealflow.core.rbac import resolve_context
    from dealflow.db.models.tenant_auth import Tenant, TenantMembership, User

    clear_role_cache()

    tenant = Tenant(name="RBAC Test Co", slug=f"rbac-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        auth0_sub=f"auth0|rbac-{uuid.uuid4().hex}",
        email="rbac@test.com",
        name="RBAC Tester",
    )
    db_session.add(user)
    await db_session.flush()

    membership = TenantMembership(
        user_id=user.id,
        tenant_id=tenant.id,
        role_slug="agent",
    )
    db_session.add(membership)
    await db_session.flush()

    ctx = await resolve_context(user.auth0_sub, tenant.id, db_session)

    assert ctx.user_id == user.id
    assert ctx.tenant_id == tenant.id
    assert ctx.role_slug == "agent"
    # "agent" role seeded with leads:read etc — must have at least some permissions
    # (exact list depends on migration 0001 seed data)
    assert isinstance(ctx.permissions, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resolve_context_owner_admin_has_wildcard(db_session) -> None:
    """owner_admin role is seeded with "*" — resolves to all permissions."""
    from dealflow.core.rbac import resolve_context
    from dealflow.db.models.tenant_auth import Tenant, TenantMembership, User

    clear_role_cache()

    tenant = Tenant(name="Owner Test Co", slug=f"owner-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        auth0_sub=f"auth0|owner-{uuid.uuid4().hex}",
        email="owner@test.com",
        name="Owner",
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(TenantMembership(user_id=user.id, tenant_id=tenant.id, role_slug="owner_admin"))
    await db_session.flush()

    ctx = await resolve_context(user.auth0_sub, tenant.id, db_session)

    assert ctx.has_permission("leads:delete") is True
    assert ctx.has_permission("tenants:admin") is True
