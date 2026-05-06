"""DAI-022: Tests for TimelineService and the notes endpoint."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from dealflow.config import Settings
from dealflow.core.dependencies import get_session, get_tenant_context
from dealflow.core.rbac import RequestContext
from dealflow.main import create_app

# ── fixtures ──────────────────────────────────────────────────────────────────

_TENANT_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()
_LEAD_ID = uuid.uuid4()


def _ctx(permissions: list[str] | None = None) -> RequestContext:
    return RequestContext(
        user_id=_USER_ID,
        auth0_sub="auth0|test",
        tenant_id=_TENANT_ID,
        role_slug="agent",
        permissions=permissions if permissions is not None else ["leads:write"],
    )


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://x:x@localhost/x",
        auth0_domain="test.auth0.com",
        auth0_audience="https://api.dealflow.test",
        secret_key="test-secret",
        environment="test",
    )


@pytest.fixture
async def notes_client(test_settings: Settings) -> AsyncClient:
    app = create_app(test_settings)
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_tenant_context] = lambda: _ctx()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── POST /api/v1/leads/{id}/notes ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_note_returns_201(notes_client: AsyncClient) -> None:
    """Happy path: note is created and timeline event is returned."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline

    fake_entry = MagicMock(spec=ActivityTimeline)
    fake_entry.id = uuid.uuid4()
    fake_entry.event_type = "lead.note_added"
    fake_entry.event_data = {"text": "called client"}
    fake_entry.actor_type = "user"
    fake_entry.occurred_at = __import__("datetime").datetime.now(
        tz=__import__("datetime").timezone.utc
    )

    with patch(
        "dealflow.api.v1.routes.leads.TimelineService.add_note",
        new=AsyncMock(return_value=fake_entry),
    ):
        resp = await notes_client.post(
            f"/api/v1/leads/{_LEAD_ID}/notes",
            json={"text": "called client"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["event_type"] == "lead.note_added"
    assert body["event_data"]["text"] == "called client"


@pytest.mark.asyncio
async def test_add_note_returns_404_when_lead_not_found(notes_client: AsyncClient) -> None:
    """Service raising lead_not_found must produce 404."""
    from dealflow.core.errors import AppError

    with patch(
        "dealflow.api.v1.routes.leads.TimelineService.add_note",
        new=AsyncMock(side_effect=AppError("lead_not_found", "Not found", 404)),
    ):
        resp = await notes_client.post(
            f"/api/v1/leads/{uuid.uuid4()}/notes",
            json={"text": "hello"},
        )

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "lead_not_found"


@pytest.mark.asyncio
async def test_add_note_requires_leads_write_permission(test_settings: Settings) -> None:
    """A context without leads:write must receive 403."""
    app = create_app(test_settings)
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_tenant_context] = lambda: _ctx(permissions=["leads:read"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/leads/{_LEAD_ID}/notes",
            json={"text": "hello"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_note_rejects_empty_text(notes_client: AsyncClient) -> None:
    """Empty text string must be rejected by Pydantic validation (422)."""
    resp = await notes_client.post(
        f"/api/v1/leads/{_LEAD_ID}/notes",
        json={"text": ""},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_add_note_passes_text_to_service(notes_client: AsyncClient) -> None:
    """The text body field is forwarded verbatim to the service."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline

    fake_entry = MagicMock(spec=ActivityTimeline)
    fake_entry.id = uuid.uuid4()
    fake_entry.event_type = "lead.note_added"
    fake_entry.event_data = {"text": "follow up booked"}
    fake_entry.actor_type = "user"
    fake_entry.occurred_at = __import__("datetime").datetime.now(
        tz=__import__("datetime").timezone.utc
    )

    with patch(
        "dealflow.api.v1.routes.leads.TimelineService.add_note",
        new=AsyncMock(return_value=fake_entry),
    ) as mock_svc:
        await notes_client.post(
            f"/api/v1/leads/{_LEAD_ID}/notes",
            json={"text": "follow up booked"},
        )

    mock_svc.assert_awaited_once_with(_LEAD_ID, "follow up booked")


# ── TimelineService unit tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_timeline_log_creates_entry() -> None:
    """log() adds an ActivityTimeline row with the correct fields."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline
    from dealflow.services.timeline import TimelineService

    session = AsyncMock()
    session.add = MagicMock()

    service = TimelineService(session, _TENANT_ID, actor_id=_USER_ID, actor_type="user")
    entry = service.log(_LEAD_ID, "lead.test_event", {"key": "val"})

    assert isinstance(entry, ActivityTimeline)
    assert entry.event_type == "lead.test_event"
    assert entry.event_data == {"key": "val"}
    assert entry.actor_type == "user"
    assert entry.actor_id == _USER_ID
    assert entry.tenant_id == _TENANT_ID
    assert entry.lead_id == _LEAD_ID
    session.add.assert_called_once_with(entry)


@pytest.mark.asyncio
async def test_timeline_log_uses_system_actor_by_default() -> None:
    """Default actor_type is 'system' with no actor_id."""
    from dealflow.services.timeline import TimelineService

    session = AsyncMock()
    session.add = MagicMock()

    service = TimelineService(session, _TENANT_ID)
    entry = service.log(_LEAD_ID, "lead.created")

    assert entry.actor_type == "system"
    assert entry.actor_id is None


@pytest.mark.asyncio
async def test_service_add_note_creates_note_event() -> None:
    """add_note() creates a lead.note_added event after verifying lead exists."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline
    from dealflow.db.models.lead_ingestion import Lead
    from dealflow.services.timeline import TimelineService

    lead = MagicMock(spec=Lead)
    result = MagicMock()
    result.scalar_one_or_none.return_value = lead
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()

    service = TimelineService(session, _TENANT_ID, actor_id=_USER_ID, actor_type="user")
    entry = await service.add_note(_LEAD_ID, "test note")

    assert isinstance(entry, ActivityTimeline)
    assert entry.event_type == "lead.note_added"
    assert entry.event_data == {"text": "test note"}
    session.flush.assert_called()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_service_add_note_raises_for_missing_lead() -> None:
    """add_note() raises lead_not_found when lead doesn't exist under the tenant."""
    from dealflow.core.errors import AppError
    from dealflow.services.timeline import TimelineService

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()

    service = TimelineService(session, _TENANT_ID)
    with pytest.raises(AppError) as exc_info:
        await service.add_note(_LEAD_ID, "hello")

    assert exc_info.value.code == "lead_not_found"
    session.add.assert_not_called()


# ── WebhookService lead.created event ────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_service_logs_lead_created_event() -> None:
    """A successful ingest writes a lead.created ActivityTimeline entry."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline
    from dealflow.db.models.lead_ingestion import LeadSource
    from dealflow.services.webhooks import WebhookService

    fake_source = MagicMock(spec=LeadSource)
    fake_source.secret_hash = None
    fake_source.tenant_id = _TENANT_ID
    fake_source.id = uuid.uuid4()

    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = fake_source

    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = None  # not a duplicate

    contact_result = MagicMock()
    contact_result.scalar_one_or_none.return_value = None  # no existing contact

    # Use real model constructors — patching them breaks sa.select() calls that
    # reference the same module-level names.
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[source_result, dup_result, contact_result])
    session.add = MagicMock()

    service = WebhookService(session)
    await service.ingest(
        source_key="src",
        payload={"email": "a@b.com", "lead_type": "buyer"},
        raw_body=b"{}",
        idempotency_key="k1",
    )

    added_types = [type(call.args[0]) for call in session.add.call_args_list]
    assert ActivityTimeline in added_types
    timeline_entry = next(
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], ActivityTimeline)
    )
    assert timeline_entry.event_type == "lead.created"
