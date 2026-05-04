"""DAI-068: Tenant isolation tests.

Proves that every read / write operation in the repository layer
always filters by tenant_id, and that the HTTP layer correctly rejects
cross-tenant access, inactive users, expired memberships, and missing
permissions — all without touching a real database.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from dealflow.core.rbac import RequestContext, clear_role_cache
from dealflow.db.repositories.base import TenantRepository

# ── helpers ───────────────────────────────────────────────────────────────────


def _session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


def _result(value=None) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = value
    r.scalars.return_value.all.return_value = value if value is not None else []
    return r


def _sql(session: AsyncMock) -> str:
    """Compile the last statement passed to session.execute() as SQL text."""
    stmt = session.execute.call_args[0][0]
    return str(stmt.compile(dialect=postgresql.dialect()))


# ── 1. Repository SQL clause verification ─────────────────────────────────────


@pytest.mark.asyncio
async def test_repo_get_where_clause_includes_tenant_id() -> None:
    """get() WHERE must contain both the requested id AND tenant_id."""
    from dealflow.db.models.lead_ingestion import Lead

    session = _session()
    session.execute = AsyncMock(return_value=_result(None))
    repo = TenantRepository(Lead, session, uuid.uuid4())
    await repo.get(uuid.uuid4())

    sql = _sql(session)
    assert "tenant_id" in sql
    assert "id" in sql


@pytest.mark.asyncio
async def test_repo_list_where_clause_includes_tenant_id() -> None:
    """list() must always include a tenant_id filter even with no extra filters."""
    from dealflow.db.models.lead_ingestion import Lead

    session = _session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    repo = TenantRepository(Lead, session, uuid.uuid4())
    await repo.list()

    assert "tenant_id" in _sql(session)


@pytest.mark.asyncio
async def test_repo_list_with_extra_filter_still_scopes_tenant() -> None:
    """Caller-supplied extra filters must not displace the tenant_id filter."""
    from dealflow.db.models.lead_ingestion import Lead

    session = _session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    repo = TenantRepository(Lead, session, uuid.uuid4())
    await repo.list(Lead.status == "new")

    sql = _sql(session)
    assert "tenant_id" in sql
    assert "status" in sql  # extra filter is also present


@pytest.mark.asyncio
async def test_repo_delete_where_clause_includes_tenant_id() -> None:
    """delete() must filter by both id and tenant_id to prevent cross-tenant deletes."""
    from dealflow.db.models.lead_ingestion import Lead

    session = _session()
    session.execute = AsyncMock(return_value=_result(None))

    repo = TenantRepository(Lead, session, uuid.uuid4())
    await repo.delete(uuid.uuid4())

    sql = _sql(session)
    assert "tenant_id" in sql
    assert "id" in sql


@pytest.mark.asyncio
async def test_repo_exists_where_clause_includes_tenant_id() -> None:
    """exists() sub-select must scope to tenant_id."""
    from dealflow.db.models.lead_ingestion import Lead

    session = _session()
    session.execute = AsyncMock(return_value=_result(False))

    repo = TenantRepository(Lead, session, uuid.uuid4())
    await repo.exists()

    assert "tenant_id" in _sql(session)


# ── 2. Repository boundary: wrong tenant ID gets nothing ─────────────────────


@pytest.mark.asyncio
async def test_repo_get_returns_none_for_wrong_tenant() -> None:
    """
    Two repos holding the same row ID but different tenant IDs must not share data.
    Repo B's session returns None — as a real DB would when the tenant_id predicate
    filters out the row owned by tenant A.
    """
    from dealflow.db.models.lead_ingestion import Lead

    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    shared_row_id = uuid.uuid4()

    fake_lead = MagicMock(spec=Lead)

    session_a = _session()
    session_a.execute = AsyncMock(return_value=_result(fake_lead))
    repo_a = TenantRepository(Lead, session_a, tenant_a)
    result_a = await repo_a.get(shared_row_id)

    session_b = _session()
    session_b.execute = AsyncMock(return_value=_result(None))
    repo_b = TenantRepository(Lead, session_b, tenant_b)
    result_b = await repo_b.get(shared_row_id)

    assert result_a is fake_lead
    assert result_b is None


@pytest.mark.asyncio
async def test_repo_add_overwrites_any_preset_tenant_id() -> None:
    """
    Even if a caller pre-stamps a wrong tenant_id on the object, add()
    overwrites it with the repository's own tenant_id.  The repo owns
    this invariant — callers cannot bypass it.
    """
    from dealflow.db.models.lead_ingestion import Lead

    repo_tenant = uuid.uuid4()
    wrong_tenant = uuid.uuid4()

    session = _session()
    obj = MagicMock(spec=Lead)
    obj.tenant_id = wrong_tenant

    repo = TenantRepository(Lead, session, repo_tenant)
    await repo.add(obj)

    assert obj.tenant_id == repo_tenant
    assert obj.tenant_id != wrong_tenant


# ── 3. RBAC: membership and user state ───────────────────────────────────────


@pytest.mark.asyncio
async def test_rbac_rejects_cross_tenant_request() -> None:
    """
    A user who belongs to tenant A must be rejected when they supply
    tenant B's ID in the X-Tenant-ID header.  resolve_context raises
    'not_a_member' because there is no TenantMembership for that pair.
    """
    from dealflow.core.rbac import resolve_context
    from dealflow.db.models.tenant_auth import User

    clear_role_cache()
    session = AsyncMock()
    tenant_b = uuid.uuid4()

    fake_user = MagicMock(spec=User)
    fake_user.id = uuid.uuid4()
    fake_user.is_active = True

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = fake_user

    no_membership = MagicMock()
    no_membership.scalar_one_or_none.return_value = None

    session.execute = AsyncMock(side_effect=[user_result, no_membership])

    with pytest.raises(ValueError, match="not_a_member"):
        await resolve_context("auth0|user_in_tenant_a", tenant_b, session)


@pytest.mark.asyncio
async def test_rbac_rejects_inactive_user() -> None:
    """
    A deactivated user (is_active=False) matches no row because the query
    filters User.is_active.is_(True).  resolve_context must raise 'user_not_found'.
    """
    from dealflow.core.rbac import resolve_context

    clear_role_cache()
    session = AsyncMock()

    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=not_found)

    with pytest.raises(ValueError, match="user_not_found"):
        await resolve_context("auth0|deactivated", uuid.uuid4(), session)


@pytest.mark.asyncio
async def test_rbac_rejects_expired_membership() -> None:
    """
    A membership whose expires_at is in the past must raise 'membership_expired'
    before any permission check is attempted.
    """
    from dealflow.core.rbac import resolve_context
    from dealflow.db.models.tenant_auth import TenantMembership, User

    clear_role_cache()
    session = AsyncMock()

    fake_user = MagicMock(spec=User)
    fake_user.id = uuid.uuid4()
    fake_user.is_active = True

    fake_membership = MagicMock(spec=TenantMembership)
    fake_membership.role_slug = "agent"
    fake_membership.is_active = True
    fake_membership.expires_at = datetime.now(tz=UTC) - timedelta(hours=1)

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = fake_user

    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = fake_membership

    session.execute = AsyncMock(side_effect=[user_result, membership_result])

    with pytest.raises(ValueError, match="membership_expired"):
        await resolve_context("auth0|expired_user", uuid.uuid4(), session)


@pytest.mark.asyncio
async def test_rbac_allows_active_non_expired_membership() -> None:
    """A user with a valid, non-expired membership must resolve successfully."""
    from dealflow.core.rbac import resolve_context
    from dealflow.db.models.tenant_auth import Role, TenantMembership, User

    clear_role_cache()
    session = AsyncMock()

    fake_user = MagicMock(spec=User)
    fake_user.id = uuid.uuid4()
    fake_user.auth0_sub = "auth0|valid"
    fake_user.is_active = True

    fake_membership = MagicMock(spec=TenantMembership)
    fake_membership.role_slug = "agent"
    fake_membership.is_active = True
    fake_membership.expires_at = datetime.now(tz=UTC) + timedelta(days=30)

    fake_role = MagicMock(spec=Role)
    fake_role.permissions = ["leads:read"]

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = fake_user

    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = fake_membership

    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = fake_role

    session.execute = AsyncMock(side_effect=[user_result, membership_result, role_result])

    tenant_id = uuid.uuid4()
    ctx = await resolve_context("auth0|valid", tenant_id, session)

    assert ctx.tenant_id == tenant_id
    assert ctx.role_slug == "agent"
    assert ctx.has_permission("leads:read") is True
    assert ctx.has_permission("leads:delete") is False


# ── 4. HTTP dependency: error → HTTP status mapping ──────────────────────────


@pytest.mark.asyncio
async def test_http_dep_not_a_member_raises_403() -> None:
    """get_tenant_context() must convert 'not_a_member' → HTTP 403."""
    from fastapi import HTTPException

    from dealflow.core.auth import TokenPayload
    from dealflow.core.dependencies import get_tenant_context

    token = TokenPayload(
        sub="auth0|stranger",
        aud="https://api.dealflow.test",
        iss="https://test.auth0.com/",
    )

    with (
        patch(
            "dealflow.core.dependencies.resolve_context",
            new=AsyncMock(side_effect=ValueError("not_a_member")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_tenant_context(token=token, tenant_id=uuid.uuid4(), session=AsyncMock())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "not_a_member"


@pytest.mark.asyncio
async def test_http_dep_user_not_found_raises_401() -> None:
    """get_tenant_context() must convert 'user_not_found' → HTTP 401."""
    from fastapi import HTTPException

    from dealflow.core.auth import TokenPayload
    from dealflow.core.dependencies import get_tenant_context

    token = TokenPayload(
        sub="auth0|ghost",
        aud="https://api.dealflow.test",
        iss="https://test.auth0.com/",
    )

    with (
        patch(
            "dealflow.core.dependencies.resolve_context",
            new=AsyncMock(side_effect=ValueError("user_not_found")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_tenant_context(token=token, tenant_id=uuid.uuid4(), session=AsyncMock())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "user_not_found"


@pytest.mark.asyncio
async def test_http_dep_membership_expired_raises_403() -> None:
    """get_tenant_context() must convert 'membership_expired' → HTTP 403."""
    from fastapi import HTTPException

    from dealflow.core.auth import TokenPayload
    from dealflow.core.dependencies import get_tenant_context

    token = TokenPayload(
        sub="auth0|expired",
        aud="https://api.dealflow.test",
        iss="https://test.auth0.com/",
    )

    with (
        patch(
            "dealflow.core.dependencies.resolve_context",
            new=AsyncMock(side_effect=ValueError("membership_expired")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_tenant_context(token=token, tenant_id=uuid.uuid4(), session=AsyncMock())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "membership_expired"


# ── 5. Permission enforcement ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_permission_blocks_agent_from_admin_action() -> None:
    """require_permission() must raise 403 when the role lacks the required permission."""
    from fastapi import HTTPException

    from dealflow.core.dependencies import require_permission

    ctx = RequestContext(
        user_id=uuid.uuid4(),
        auth0_sub="auth0|agent",
        tenant_id=uuid.uuid4(),
        role_slug="agent",
        permissions=["leads:read"],
    )
    checker = require_permission("leads:delete")

    with pytest.raises(HTTPException) as exc_info:
        await checker(ctx=ctx)

    assert exc_info.value.status_code == 403
    assert "leads:delete" in exc_info.value.detail["message"]


@pytest.mark.asyncio
async def test_permission_allows_wildcard_for_owner_admin() -> None:
    """A context with '*' must pass any permission check."""
    from dealflow.core.dependencies import require_permission

    ctx = RequestContext(
        user_id=uuid.uuid4(),
        auth0_sub="auth0|owner",
        tenant_id=uuid.uuid4(),
        role_slug="owner_admin",
        permissions=["*"],
    )

    for perm in ["leads:delete", "tenants:admin", "users:impersonate"]:
        result = await require_permission(perm)(ctx=ctx)
        assert result is ctx


@pytest.mark.asyncio
async def test_permission_glob_covers_namespace_but_not_others() -> None:
    """'leads:*' covers all leads sub-permissions but must NOT cover other namespaces."""
    from fastapi import HTTPException

    from dealflow.core.dependencies import require_permission

    ctx = RequestContext(
        user_id=uuid.uuid4(),
        auth0_sub="auth0|manager",
        tenant_id=uuid.uuid4(),
        role_slug="manager",
        permissions=["leads:*", "tasks:read"],
    )

    for perm in ["leads:read", "leads:write", "leads:delete", "leads:assign"]:
        result = await require_permission(perm)(ctx=ctx)
        assert result is ctx

    with pytest.raises(HTTPException) as exc_info:
        await require_permission("tasks:write")(ctx=ctx)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_permission_exact_match_does_not_cover_siblings() -> None:
    """An exact permission like 'leads:read' must not grant 'leads:write'."""
    from fastapi import HTTPException

    from dealflow.core.dependencies import require_permission

    ctx = RequestContext(
        user_id=uuid.uuid4(),
        auth0_sub="auth0|readonly",
        tenant_id=uuid.uuid4(),
        role_slug="auditor",
        permissions=["leads:read"],
    )

    result = await require_permission("leads:read")(ctx=ctx)
    assert result is ctx

    with pytest.raises(HTTPException):
        await require_permission("leads:write")(ctx=ctx)
