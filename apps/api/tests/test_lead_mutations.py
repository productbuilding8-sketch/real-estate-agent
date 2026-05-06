"""DAI-021: Tests for lead mutation endpoints and service."""

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
_AGENT_ID = uuid.uuid4()


def _ctx(permissions: list[str] | None = None) -> RequestContext:
    return RequestContext(
        user_id=_USER_ID,
        auth0_sub="auth0|test",
        tenant_id=_TENANT_ID,
        role_slug="agent",
        permissions=permissions if permissions is not None else ["leads:write", "leads:assign"],
    )


def _mock_lead(status: str = "new", assigned_agent_id: uuid.UUID | None = None) -> MagicMock:
    lead = MagicMock()
    lead.id = _LEAD_ID
    lead.status = status
    lead.assigned_agent_id = assigned_agent_id
    return lead


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
async def client(test_settings: Settings) -> AsyncClient:
    app = create_app(test_settings)
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_tenant_context] = lambda: _ctx()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── PATCH /api/v1/leads/{id}/status ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_status_returns_200(client: AsyncClient) -> None:
    """Happy path: new → contacted returns 200 with updated status."""
    lead = _mock_lead(status="new")
    lead.status = "contacted"  # service mutates and returns the lead

    with patch(
        "dealflow.api.v1.routes.leads.LeadMutationService.update_status",
        new=AsyncMock(return_value=lead),
    ):
        resp = await client.patch(
            f"/api/v1/leads/{_LEAD_ID}/status",
            json={"status": "contacted"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(_LEAD_ID)
    assert body["status"] == "contacted"


@pytest.mark.asyncio
async def test_update_status_returns_409_on_invalid_transition(client: AsyncClient) -> None:
    """Service raising invalid_transition must produce 409."""
    from dealflow.core.errors import AppError

    with patch(
        "dealflow.api.v1.routes.leads.LeadMutationService.update_status",
        new=AsyncMock(
            side_effect=AppError("invalid_transition", "Cannot transition", 409)
        ),
    ):
        resp = await client.patch(
            f"/api/v1/leads/{_LEAD_ID}/status",
            json={"status": "new"},
        )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_transition"


@pytest.mark.asyncio
async def test_update_status_returns_422_on_unknown_status(client: AsyncClient) -> None:
    """Service raising invalid_status must produce 422."""
    from dealflow.core.errors import AppError

    with patch(
        "dealflow.api.v1.routes.leads.LeadMutationService.update_status",
        new=AsyncMock(
            side_effect=AppError("invalid_status", "Unknown status", 422)
        ),
    ):
        resp = await client.patch(
            f"/api/v1/leads/{_LEAD_ID}/status",
            json={"status": "foobar"},
        )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_update_status_returns_404_when_not_found(client: AsyncClient) -> None:
    """Service raising lead_not_found must produce 404."""
    from dealflow.core.errors import AppError

    with patch(
        "dealflow.api.v1.routes.leads.LeadMutationService.update_status",
        new=AsyncMock(side_effect=AppError("lead_not_found", "Not found", 404)),
    ):
        resp = await client.patch(
            f"/api/v1/leads/{uuid.uuid4()}/status",
            json={"status": "contacted"},
        )

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "lead_not_found"


@pytest.mark.asyncio
async def test_update_status_requires_permission(test_settings: Settings) -> None:
    """A context without leads:write must receive 403."""
    app = create_app(test_settings)
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_tenant_context] = lambda: _ctx(permissions=["leads:read"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/leads/{_LEAD_ID}/status",
            json={"status": "contacted"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_status_passes_reason(client: AsyncClient) -> None:
    """reason field is forwarded to the service."""
    lead = _mock_lead(status="lost")

    with patch(
        "dealflow.api.v1.routes.leads.LeadMutationService.update_status",
        new=AsyncMock(return_value=lead),
    ) as mock_svc:
        await client.patch(
            f"/api/v1/leads/{_LEAD_ID}/status",
            json={"status": "lost", "reason": "no budget"},
        )

    mock_svc.assert_awaited_once_with(_LEAD_ID, "lost", "no budget")


# ── PATCH /api/v1/leads/{id}/assign ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_lead_returns_200(client: AsyncClient) -> None:
    """Happy path: assign to an agent returns 200 with agent_id."""
    lead = _mock_lead(assigned_agent_id=_AGENT_ID)

    with patch(
        "dealflow.api.v1.routes.leads.LeadMutationService.assign",
        new=AsyncMock(return_value=lead),
    ):
        resp = await client.patch(
            f"/api/v1/leads/{_LEAD_ID}/assign",
            json={"agent_id": str(_AGENT_ID)},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(_LEAD_ID)
    assert body["assigned_agent_id"] == str(_AGENT_ID)


@pytest.mark.asyncio
async def test_unassign_lead_returns_200(client: AsyncClient) -> None:
    """agent_id=None unassigns the lead."""
    lead = _mock_lead(assigned_agent_id=None)

    with patch(
        "dealflow.api.v1.routes.leads.LeadMutationService.assign",
        new=AsyncMock(return_value=lead),
    ):
        resp = await client.patch(
            f"/api/v1/leads/{_LEAD_ID}/assign",
            json={"agent_id": None},
        )

    assert resp.status_code == 200
    assert resp.json()["assigned_agent_id"] is None


@pytest.mark.asyncio
async def test_assign_requires_permission(test_settings: Settings) -> None:
    """A context without leads:assign must receive 403."""
    app = create_app(test_settings)
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[get_tenant_context] = lambda: _ctx(permissions=["leads:read"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/leads/{_LEAD_ID}/assign",
            json={"agent_id": str(_AGENT_ID)},
        )

    assert resp.status_code == 403


# ── LeadMutationService unit tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_service_update_status_logs_timeline() -> None:
    """Successful status update adds one ActivityTimeline row."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline
    from dealflow.services.lead_mutations import LeadMutationService

    lead = MagicMock()
    lead.status = "new"
    lead.id = _LEAD_ID

    result = MagicMock()
    result.scalar_one_or_none.return_value = lead
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    service = LeadMutationService(session, _TENANT_ID, _USER_ID)
    await service.update_status(_LEAD_ID, "contacted", reason="first call made")

    assert lead.status == "contacted"
    session.add.assert_called_once()
    event = session.add.call_args[0][0]
    assert isinstance(event, ActivityTimeline)
    assert event.event_type == "lead.status_changed"
    assert event.event_data["from"] == "new"
    assert event.event_data["to"] == "contacted"
    assert event.event_data["reason"] == "first call made"


@pytest.mark.asyncio
async def test_service_invalid_transition_raises() -> None:
    """Transitioning qualified → new raises AppError with code invalid_transition."""
    from dealflow.core.errors import AppError
    from dealflow.services.lead_mutations import LeadMutationService

    lead = MagicMock()
    lead.status = "qualified"
    lead.id = _LEAD_ID

    result = MagicMock()
    result.scalar_one_or_none.return_value = lead
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    service = LeadMutationService(session, _TENANT_ID, _USER_ID)
    with pytest.raises(AppError) as exc_info:
        await service.update_status(_LEAD_ID, "new")
    assert exc_info.value.code == "invalid_transition"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_service_unknown_status_raises() -> None:
    """Passing an unrecognised status raises AppError with code invalid_status."""
    from dealflow.core.errors import AppError
    from dealflow.services.lead_mutations import LeadMutationService

    session = AsyncMock()
    service = LeadMutationService(session, _TENANT_ID, _USER_ID)
    with pytest.raises(AppError) as exc_info:
        await service.update_status(_LEAD_ID, "foobar")
    assert exc_info.value.code == "invalid_status"
    assert exc_info.value.status_code == 422
    session.execute.assert_not_called()  # no DB hit before validation


@pytest.mark.asyncio
async def test_service_assign_logs_timeline() -> None:
    """Successful assignment adds one ActivityTimeline row with correct event type."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline
    from dealflow.services.lead_mutations import LeadMutationService

    lead = MagicMock()
    lead.id = _LEAD_ID
    lead.assigned_agent_id = None

    result = MagicMock()
    result.scalar_one_or_none.return_value = lead
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    service = LeadMutationService(session, _TENANT_ID, _USER_ID)
    await service.assign(_LEAD_ID, _AGENT_ID)

    assert lead.assigned_agent_id == _AGENT_ID
    session.add.assert_called_once()
    event = session.add.call_args[0][0]
    assert isinstance(event, ActivityTimeline)
    assert event.event_type == "lead.assigned"
    assert event.event_data["agent_id"] == str(_AGENT_ID)


@pytest.mark.asyncio
async def test_service_unassign_logs_unassigned_event() -> None:
    """Passing agent_id=None logs a lead.unassigned event."""
    from dealflow.db.models.audit_knowledge import ActivityTimeline
    from dealflow.services.lead_mutations import LeadMutationService

    lead = MagicMock()
    lead.id = _LEAD_ID
    lead.assigned_agent_id = _AGENT_ID

    result = MagicMock()
    result.scalar_one_or_none.return_value = lead
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    service = LeadMutationService(session, _TENANT_ID, _USER_ID)
    await service.assign(_LEAD_ID, None)

    event = session.add.call_args[0][0]
    assert isinstance(event, ActivityTimeline)
    assert event.event_type == "lead.unassigned"
    assert event.event_data["agent_id"] is None
    assert event.event_data["previous_agent_id"] == str(_AGENT_ID)


@pytest.mark.asyncio
async def test_service_load_raises_for_wrong_tenant() -> None:
    """_load raises lead_not_found when the lead belongs to a different tenant."""
    from dealflow.core.errors import AppError
    from dealflow.services.lead_mutations import LeadMutationService

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    service = LeadMutationService(session, uuid.uuid4(), _USER_ID)
    with pytest.raises(AppError) as exc_info:
        await service.update_status(_LEAD_ID, "contacted")
    assert exc_info.value.code == "lead_not_found"
