"""Unit tests for TenantRepository[T] base class."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa

from dealflow.db.repositories.base import TenantRepository
from dealflow.db.session import Base


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_session() -> AsyncMock:
    """Return an AsyncSession mock where execute() returns a MagicMock result."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_result(value=None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    result.scalars.return_value.all.return_value = value if value is not None else []
    return result


# ── unit: constructor guards ──────────────────────────────────────────────────

def test_init_rejects_model_without_tenant_id() -> None:
    """Models without tenant_id must not be wrapped — catch misconfiguration early."""
    class NoTenant(Base):
        __tablename__ = "no_tenant_test"
        id = sa.Column(sa.Integer, primary_key=True)

    session = _make_session()
    with pytest.raises(TypeError, match="tenant_id"):
        TenantRepository(NoTenant, session, uuid.uuid4())


def test_init_accepts_model_with_tenant_id() -> None:
    from dealflow.db.models.lead_ingestion import Lead
    session = _make_session()
    repo = TenantRepository(Lead, session, uuid.uuid4())
    assert repo._model is Lead


# ── unit: get ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_returns_row_when_found() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    tenant_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    fake_lead = MagicMock(spec=Lead)

    session = _make_session()
    session.execute = AsyncMock(return_value=_make_result(fake_lead))

    repo = TenantRepository(Lead, session, tenant_id)
    result = await repo.get(lead_id)

    assert result is fake_lead
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_returns_none_when_not_found() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    session = _make_session()
    session.execute = AsyncMock(return_value=_make_result(None))

    repo = TenantRepository(Lead, session, uuid.uuid4())
    result = await repo.get(uuid.uuid4())

    assert result is None


# ── unit: list ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_returns_rows() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    tenant_id = uuid.uuid4()
    fake_leads = [MagicMock(spec=Lead), MagicMock(spec=Lead)]

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = fake_leads

    session = _make_session()
    session.execute = AsyncMock(return_value=result_mock)

    repo = TenantRepository(Lead, session, tenant_id)
    rows = await repo.list()

    assert rows == fake_leads
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_with_cursor_passes_through() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []

    session = _make_session()
    session.execute = AsyncMock(return_value=result_mock)

    repo = TenantRepository(Lead, session, uuid.uuid4())
    rows = await repo.list(cursor=uuid.uuid4())

    assert rows == []
    session.execute.assert_awaited_once()


# ── unit: add ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_stamps_tenant_id() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    tenant_id = uuid.uuid4()
    session = _make_session()

    lead = MagicMock(spec=Lead)
    repo = TenantRepository(Lead, session, tenant_id)
    await repo.add(lead)

    assert lead.tenant_id == tenant_id
    session.add.assert_called_once_with(lead)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(lead)


# ── unit: delete ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_returns_true_when_row_deleted() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    deleted_id = uuid.uuid4()
    session = _make_session()
    session.execute = AsyncMock(return_value=_make_result(deleted_id))

    repo = TenantRepository(Lead, session, uuid.uuid4())
    deleted = await repo.delete(deleted_id)

    assert deleted is True


@pytest.mark.asyncio
async def test_delete_returns_false_when_row_not_found() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    session = _make_session()
    session.execute = AsyncMock(return_value=_make_result(None))

    repo = TenantRepository(Lead, session, uuid.uuid4())
    deleted = await repo.delete(uuid.uuid4())

    assert deleted is False


# ── unit: exists ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exists_returns_true() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    session = _make_session()
    session.execute = AsyncMock(return_value=_make_result(True))

    repo = TenantRepository(Lead, session, uuid.uuid4())
    assert await repo.exists() is True


@pytest.mark.asyncio
async def test_exists_returns_false() -> None:
    from dealflow.db.models.lead_ingestion import Lead

    session = _make_session()
    session.execute = AsyncMock(return_value=_make_result(False))

    repo = TenantRepository(Lead, session, uuid.uuid4())
    assert await repo.exists() is False


# ── integration: real DB ──────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_and_get_with_real_db(db_session) -> None:
    from dealflow.db.models.lead_ingestion import Contact, Lead, LeadSource
    from dealflow.db.models.tenant_auth import Tenant

    tenant = Tenant(name="Repo Test Tenant", slug=f"repo-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.flush()

    source = LeadSource(
        tenant_id=tenant.id,
        type="webhook",
        name="Test Source",
        source_key=f"src-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(source)

    contact = Contact(tenant_id=tenant.id, first_name="Jane", last_name="Doe")
    db_session.add(contact)
    await db_session.flush()

    lead = Lead(
        contact_id=contact.id,
        source_id=source.id,
        status="new",
    )

    repo = TenantRepository(Lead, db_session, tenant.id)
    created = await repo.add(lead)

    assert created.id is not None
    assert created.tenant_id == tenant.id

    fetched = await repo.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_does_not_cross_tenant_boundary(db_session) -> None:
    """A row owned by tenant A must not be visible to tenant B's repository."""
    from dealflow.db.models.lead_ingestion import Contact, Lead, LeadSource
    from dealflow.db.models.tenant_auth import Tenant

    tenant_a = Tenant(name="Tenant A", slug=f"ta-{uuid.uuid4().hex[:8]}")
    tenant_b = Tenant(name="Tenant B", slug=f"tb-{uuid.uuid4().hex[:8]}")
    db_session.add_all([tenant_a, tenant_b])
    await db_session.flush()

    source = LeadSource(
        tenant_id=tenant_a.id,
        type="webhook",
        name="Src A",
        source_key=f"src-{uuid.uuid4().hex[:8]}",
    )
    contact = Contact(tenant_id=tenant_a.id, first_name="Cross", last_name="Check")
    db_session.add_all([source, contact])
    await db_session.flush()

    lead = Lead(contact_id=contact.id, source_id=source.id, status="new")
    repo_a = TenantRepository(Lead, db_session, tenant_a.id)
    created = await repo_a.add(lead)

    repo_b = TenantRepository(Lead, db_session, tenant_b.id)
    fetched = await repo_b.get(created.id)
    assert fetched is None  # tenant B cannot see tenant A's lead
