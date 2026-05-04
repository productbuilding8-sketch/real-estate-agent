"""DAI-058: AuditService tests.

Unit tests mock the DB session — no Postgres required.
Integration tests (marked) require Docker + running Postgres.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from dealflow.services.audit import AuditService

# ── unit: log() ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_creates_audit_entry() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    svc = AuditService(session, tenant_id=tenant_id)
    entry = await svc.log(
        action="lead.created",
        entity_type="lead",
        entity_id=entity_id,
        after={"status": "new"},
        actor_id=actor_id,
        actor_type="user",
    )

    session.add.assert_called_once_with(entry)
    session.flush.assert_awaited_once()

    assert entry.tenant_id == tenant_id
    assert entry.actor_id == actor_id
    assert entry.actor_type == "user"
    assert entry.action == "lead.created"
    assert entry.entity_type == "lead"
    assert entry.entity_id == entity_id
    assert entry.after_state == {"status": "new"}
    assert entry.before_state is None
    assert entry.pii_fields_scrubbed is False


@pytest.mark.asyncio
async def test_log_before_and_after_state() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = AuditService(session, tenant_id=uuid.uuid4())
    entry = await svc.log(
        action="lead.status_changed",
        entity_type="lead",
        entity_id=uuid.uuid4(),
        before={"status": "new"},
        after={"status": "qualified"},
    )

    assert entry.before_state == {"status": "new"}
    assert entry.after_state == {"status": "qualified"}


@pytest.mark.asyncio
async def test_log_defaults_actor_type_to_system() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = AuditService(session, tenant_id=uuid.uuid4())
    entry = await svc.log(
        action="lead.auto_scored",
        entity_type="lead",
        entity_id=uuid.uuid4(),
    )

    assert entry.actor_type == "system"
    assert entry.actor_id is None


@pytest.mark.asyncio
async def test_log_captures_ip_address() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = AuditService(session, tenant_id=uuid.uuid4())
    entry = await svc.log(
        action="lead.created",
        entity_type="lead",
        entity_id=uuid.uuid4(),
        ip_address="203.0.113.42",
    )

    assert entry.ip_address == "203.0.113.42"


@pytest.mark.asyncio
async def test_log_pii_scrubbed_starts_false() -> None:
    """Every new audit log entry must be flagged for PII scrubbing by the worker."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = AuditService(session, tenant_id=uuid.uuid4())
    entry = await svc.log(
        action="contact.created",
        entity_type="contact",
        entity_id=uuid.uuid4(),
        after={"email": "pii@example.com", "phone": "+15551234567"},
    )

    assert entry.pii_fields_scrubbed is False


# ── unit: add_timeline_event() ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_timeline_event_basic() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    tenant_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    svc = AuditService(session, tenant_id=tenant_id)
    event = await svc.add_timeline_event(
        lead_id=lead_id,
        event_type="message.sent",
        event_data={"channel": "sms", "body": "Hello!"},
    )

    session.add.assert_called_once_with(event)
    session.flush.assert_awaited_once()

    assert event.tenant_id == tenant_id
    assert event.lead_id == lead_id
    assert event.event_type == "message.sent"
    assert event.event_data == {"channel": "sms", "body": "Hello!"}
    assert event.visible_to_agent is True
    assert event.actor_type == "system"


@pytest.mark.asyncio
async def test_add_timeline_event_not_visible_to_agent() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = AuditService(session, tenant_id=uuid.uuid4())
    event = await svc.add_timeline_event(
        lead_id=uuid.uuid4(),
        event_type="system.dedup_check",
        visible_to_agent=False,
    )

    assert event.visible_to_agent is False


@pytest.mark.asyncio
async def test_add_timeline_event_explicit_occurred_at() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    occurred = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
    svc = AuditService(session, tenant_id=uuid.uuid4())
    event = await svc.add_timeline_event(
        lead_id=uuid.uuid4(),
        event_type="appointment.scheduled",
        occurred_at=occurred,
    )

    assert event.occurred_at == occurred


@pytest.mark.asyncio
async def test_add_timeline_event_defaults_occurred_at_to_now() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    before = datetime.now(tz=UTC)
    svc = AuditService(session, tenant_id=uuid.uuid4())
    event = await svc.add_timeline_event(
        lead_id=uuid.uuid4(),
        event_type="lead.viewed",
    )
    after = datetime.now(tz=UTC)

    assert event.occurred_at is not None
    assert before <= event.occurred_at <= after


@pytest.mark.asyncio
async def test_add_timeline_event_with_actor() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    actor_id = uuid.uuid4()
    svc = AuditService(session, tenant_id=uuid.uuid4())
    event = await svc.add_timeline_event(
        lead_id=uuid.uuid4(),
        event_type="note.added",
        actor_id=actor_id,
        actor_type="user",
    )

    assert event.actor_id == actor_id
    assert event.actor_type == "user"


# ── integration: real DB ──────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_log_persisted_to_db(db_session) -> None:
    import sqlalchemy as sa

    from dealflow.db.models.audit_knowledge import AuditLog
    from dealflow.db.models.tenant_auth import Tenant

    tenant = Tenant(name="Audit Test", slug=f"audit-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.flush()

    svc = AuditService(db_session, tenant_id=tenant.id)
    entry = await svc.log(
        action="lead.created",
        entity_type="lead",
        entity_id=uuid.uuid4(),
        after={"status": "new"},
    )

    result = await db_session.execute(sa.select(AuditLog).where(AuditLog.id == entry.id))
    persisted = result.scalar_one_or_none()

    assert persisted is not None
    assert persisted.action == "lead.created"
    assert persisted.tenant_id == tenant.id
    assert persisted.pii_fields_scrubbed is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_timeline_event_persisted_to_db(db_session) -> None:
    import sqlalchemy as sa

    from dealflow.db.models.audit_knowledge import ActivityTimeline
    from dealflow.db.models.lead_ingestion import Contact, Lead, LeadSource
    from dealflow.db.models.tenant_auth import Tenant

    tenant = Tenant(name="Timeline Test", slug=f"tl-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.flush()

    source = LeadSource(
        tenant_id=tenant.id,
        type="webhook",
        name="Src",
        source_key=f"s-{uuid.uuid4().hex[:8]}",
    )
    contact = Contact(tenant_id=tenant.id, first_name="Tim", last_name="Line")
    db_session.add_all([source, contact])
    await db_session.flush()

    lead = Lead(
        tenant_id=tenant.id,
        contact_id=contact.id,
        source_id=source.id,
        status="new",
    )
    db_session.add(lead)
    await db_session.flush()

    svc = AuditService(db_session, tenant_id=tenant.id)
    event = await svc.add_timeline_event(
        lead_id=lead.id,
        event_type="lead.created",
        event_data={"source": "webhook"},
    )

    result = await db_session.execute(
        sa.select(ActivityTimeline).where(ActivityTimeline.id == event.id)
    )
    persisted = result.scalar_one_or_none()

    assert persisted is not None
    assert persisted.event_type == "lead.created"
    assert persisted.lead_id == lead.id
    assert persisted.tenant_id == tenant.id
