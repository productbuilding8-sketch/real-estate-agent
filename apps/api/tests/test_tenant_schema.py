"""DAI-011: Tenant/User/Role schema tests (V2)."""

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.db.models import (
    AgentProfile,
    Role,
    Tenant,
    TenantInvitation,
    TenantMembership,
    User,
)
from dealflow.db.session import Base


# ── unit: model metadata ──────────────────────────────────────────────────────

def test_all_models_registered_in_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "tenants", "users", "roles", "tenant_memberships",
        "agent_profiles", "tenant_invitations",
    }
    assert expected.issubset(table_names)


def test_tenant_table_columns() -> None:
    cols = {c.name for c in Tenant.__table__.columns}
    assert {"id", "name", "slug", "timezone", "is_active", "settings", "created_at", "updated_at"}.issubset(cols)


def test_user_has_no_tenant_fk() -> None:
    """V2: users are global — no tenant_id column."""
    col_names = {c.name for c in User.__table__.columns}
    assert "tenant_id" not in col_names
    assert "auth0_sub" in col_names


def test_tenant_membership_has_user_and_tenant_fk() -> None:
    fk_targets = {fk.target_fullname for fk in TenantMembership.__table__.foreign_keys}
    assert "users.id" in fk_targets
    assert "tenants.id" in fk_targets


def test_role_has_no_is_system_column() -> None:
    """V2: roles are simplified — no is_system flag, no tenant_id."""
    col_names = {c.name for c in Role.__table__.columns}
    assert "is_system" not in col_names
    assert "tenant_id" not in col_names


def test_agent_profile_has_calendar_connection_column() -> None:
    col_names = {c.name for c in AgentProfile.__table__.columns}
    assert "default_calendar_connection_id" in col_names


def test_tenant_membership_unique_constraint() -> None:
    constraint_names = {c.name for c in TenantMembership.__table__.constraints}
    assert "uq_tenant_memberships_user_tenant" in constraint_names


# ── integration: real DB (requires Docker) ────────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_tenant_and_global_user(db_session: AsyncSession) -> None:
    tenant = Tenant(name="Acme Realty", slug=f"acme-{uuid.uuid4().hex[:8]}")
    db_client.add(tenant)
    await db_client.flush()

    user = User(
        auth0_sub=f"auth0|{uuid.uuid4().hex}",
        email="alice@acme.com",
        name="Alice",
    )
    db_client.add(user)
    await db_client.flush()

    membership = TenantMembership(
        user_id=user.id,
        tenant_id=tenant.id,
        role_slug="agent",
    )
    db_client.add(membership)
    await db_client.flush()

    result = await db_client.execute(
        sa.select(TenantMembership).where(TenantMembership.tenant_id == tenant.id)
    )
    memberships = result.scalars().all()
    assert len(memberships) == 1
    assert memberships[0].role_slug == "agent"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_multi_tenant_membership(db_session: AsyncSession) -> None:
    """A single user can belong to two tenants with different roles."""
    t1 = Tenant(name="Tenant One", slug=f"t1-{uuid.uuid4().hex[:8]}")
    t2 = Tenant(name="Tenant Two", slug=f"t2-{uuid.uuid4().hex[:8]}")
    db_session.add_all([t1, t2])
    await db_session.flush()

    user = User(auth0_sub=f"auth0|{uuid.uuid4().hex}", email="bob@multi.com", name="Bob")
    db_session.add(user)
    await db_session.flush()

    m1 = TenantMembership(user_id=user.id, tenant_id=t1.id, role_slug="owner_admin")
    m2 = TenantMembership(user_id=user.id, tenant_id=t2.id, role_slug="agent")
    db_session.add_all([m1, m2])
    await db_session.flush()

    result = await db_session.execute(
        sa.select(TenantMembership).where(TenantMembership.user_id == user.id)
    )
    memberships = result.scalars().all()
    assert len(memberships) == 2
    slugs = {m.role_slug for m in memberships}
    assert slugs == {"owner_admin", "agent"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_roles_seeded(db_session: AsyncSession) -> None:
    result = await db_session.execute(sa.select(Role))
    roles = result.scalars().all()
    slugs = {r.slug for r in roles}
    assert slugs == {"owner_admin", "manager", "agent", "implementation_admin", "auditor"}
