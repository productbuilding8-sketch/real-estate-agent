"""DAI-018/019/020: Tests for leads API and webhook ingestion.

All tests are unit tests — no real DB required.
Service methods are mocked at the route level; service internals are
tested by mocking the SQLAlchemy session directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from dealflow.api.v1.schemas.leads import (
    ContactDetail,
    ContactSummary,
    LeadDetail,
    LeadListItem,
    SourceSummary,
)
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
        permissions=permissions if permissions is not None else ["leads:read"],
    )


def _lead_item(**kwargs: Any) -> LeadListItem:
    defaults: dict[str, Any] = dict(
        id=_LEAD_ID,
        status="new",
        lead_type="buyer",
        created_at=datetime.now(tz=UTC),
        contact=ContactSummary(id=uuid.uuid4(), full_name="Jane Doe", email="jane@test.com"),
        source=SourceSummary(id=uuid.uuid4(), name="Website", type="webhook"),
    )
    defaults.update(kwargs)
    return LeadListItem(**defaults)


def _lead_detail(**kwargs: Any) -> LeadDetail:
    defaults: dict[str, Any] = dict(
        id=_LEAD_ID,
        status="new",
        lead_type="buyer",
        created_at=datetime.now(tz=UTC),
        contact=ContactDetail(id=uuid.uuid4(), full_name="Jane Doe", email="jane@test.com"),
        source=SourceSummary(id=uuid.uuid4(), name="Website", type="webhook"),
    )
    defaults.update(kwargs)
    return LeadDetail(**defaults)


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
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def leads_client(test_settings: Settings, mock_session: AsyncMock) -> AsyncClient:
    """App client with DB session and tenant context overridden."""
    app = create_app(test_settings)
    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_tenant_context] = lambda: _ctx()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── GET /api/v1/leads ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_leads_returns_200(leads_client: AsyncClient) -> None:
    """Happy path: mocked service returns one item."""
    item = _lead_item()
    with (
        patch(
            "dealflow.api.v1.routes.leads.LeadService.list",
            new=AsyncMock(return_value=([item], 1)),
        ),
        patch(
            "dealflow.api.v1.routes.leads.LeadService.status_counts",
            new=AsyncMock(return_value={"new": 1}),
        ),
    ):
        resp = await leads_client.get("/api/v1/leads")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(_LEAD_ID)


@pytest.mark.asyncio
async def test_list_leads_empty(leads_client: AsyncClient) -> None:
    """Empty result set is valid — returns pages=1 min."""
    with (
        patch(
            "dealflow.api.v1.routes.leads.LeadService.list",
            new=AsyncMock(return_value=([], 0)),
        ),
        patch(
            "dealflow.api.v1.routes.leads.LeadService.status_counts",
            new=AsyncMock(return_value={}),
        ),
    ):
        resp = await leads_client.get("/api/v1/leads")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["pages"] == 1  # minimum is 1 even when empty


@pytest.mark.asyncio
async def test_list_leads_passes_filters(leads_client: AsyncClient) -> None:
    """Query params are forwarded to the service."""
    with (
        patch(
            "dealflow.api.v1.routes.leads.LeadService.list",
            new=AsyncMock(return_value=([], 0)),
        ) as mock_list,
        patch(
            "dealflow.api.v1.routes.leads.LeadService.status_counts",
            new=AsyncMock(return_value={}),
        ),
    ):
        await leads_client.get("/api/v1/leads?status=qualified&search=Jane&page=2&limit=10")

    mock_list.assert_awaited_once_with(status="qualified", search="Jane", page=2, limit=10)


@pytest.mark.asyncio
async def test_list_leads_requires_permission(test_settings: Settings) -> None:
    """A context without leads:read must receive 403."""
    app = create_app(test_settings)
    app.dependency_overrides[get_tenant_context] = lambda: _ctx(permissions=[])
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/leads")

    assert resp.status_code == 403


# ── GET /api/v1/leads/{id} ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_lead_returns_200(leads_client: AsyncClient) -> None:
    """Happy path: mocked service returns a lead detail."""
    detail = _lead_detail()
    with patch(
        "dealflow.api.v1.routes.leads.LeadService.get_detail",
        new=AsyncMock(return_value=detail),
    ):
        resp = await leads_client.get(f"/api/v1/leads/{_LEAD_ID}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(_LEAD_ID)


@pytest.mark.asyncio
async def test_get_lead_returns_404_when_not_found(leads_client: AsyncClient) -> None:
    """Service returning None must produce a 404 with code 'lead_not_found'."""
    with patch(
        "dealflow.api.v1.routes.leads.LeadService.get_detail",
        new=AsyncMock(return_value=None),
    ):
        resp = await leads_client.get(f"/api/v1/leads/{uuid.uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "lead_not_found"


@pytest.mark.asyncio
async def test_get_lead_passes_tenant_scoped_id(leads_client: AsyncClient) -> None:
    """The route must call get_detail with the lead_id from the URL."""
    target_id = uuid.uuid4()
    with patch(
        "dealflow.api.v1.routes.leads.LeadService.get_detail",
        new=AsyncMock(return_value=None),
    ) as mock_detail:
        await leads_client.get(f"/api/v1/leads/{target_id}")

    mock_detail.assert_awaited_once_with(target_id)


# ── LeadService unit tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lead_service_get_detail_returns_none_when_not_found() -> None:
    """Service returns None when the lead row is missing."""
    from dealflow.services.leads import LeadService

    session = AsyncMock()
    result = MagicMock()
    result.one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    service = LeadService(session, uuid.uuid4())
    detail = await service.get_detail(uuid.uuid4())
    assert detail is None


@pytest.mark.asyncio
async def test_lead_service_list_returns_empty_on_no_rows() -> None:
    """Service list() returns ([], 0) when the DB has no matching leads."""
    from dealflow.services.leads import LeadService

    session = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    rows_result = MagicMock()
    rows_result.all.return_value = []

    session.execute = AsyncMock(side_effect=[count_result, rows_result])

    service = LeadService(session, uuid.uuid4())
    items, total = await service.list()
    assert items == []
    assert total == 0


# ── POST /api/v1/webhooks/leads/{source_key} ─────────────────────────────────


@pytest.fixture
async def webhook_client(test_settings: Settings, mock_session: AsyncMock) -> AsyncClient:
    """App client with only DB session overridden (webhooks don't use tenant auth)."""
    app = create_app(test_settings)
    app.dependency_overrides[get_session] = lambda: mock_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_webhook_returns_404_for_unknown_source(webhook_client: AsyncClient) -> None:
    """Unknown source_key must produce a 404 with code 'source_not_found'."""
    from dealflow.core.errors import AppError

    with patch(
        "dealflow.api.v1.routes.webhooks.WebhookService.ingest",
        new=AsyncMock(side_effect=AppError("source_not_found", "Not found", 404)),
    ):
        resp = await webhook_client.post(
            "/api/v1/webhooks/leads/unknown-source",
            json={"email": "test@example.com"},
        )

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "source_not_found"


@pytest.mark.asyncio
async def test_webhook_returns_200_on_success(webhook_client: AsyncClient) -> None:
    """Successful ingestion returns the event_id and status."""
    from dealflow.db.models.lead_ingestion import IngestionEvent

    fake_event = MagicMock(spec=IngestionEvent)
    fake_event.id = uuid.uuid4()
    fake_event.status = "received"

    with patch(
        "dealflow.api.v1.routes.webhooks.WebhookService.ingest",
        new=AsyncMock(return_value=fake_event),
    ):
        resp = await webhook_client.post(
            "/api/v1/webhooks/leads/my-source",
            json={"email": "lead@example.com", "first_name": "Alice"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["event_id"] == str(fake_event.id)
    assert body["status"] == "received"


@pytest.mark.asyncio
async def test_webhook_returns_401_for_bad_signature(webhook_client: AsyncClient) -> None:
    """Invalid HMAC signature must produce 401."""
    from dealflow.core.errors import AppError

    with patch(
        "dealflow.api.v1.routes.webhooks.WebhookService.ingest",
        new=AsyncMock(side_effect=AppError("invalid_signature", "Bad signature", 401)),
    ):
        resp = await webhook_client.post(
            "/api/v1/webhooks/leads/secure-source",
            json={"email": "x@y.com"},
            headers={"X-Hub-Signature-256": "sha256=badhash"},
        )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_signature"


# ── WebhookService unit tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_service_raises_for_missing_source() -> None:
    """WebhookService.ingest() raises AppError when source_key is unknown."""
    from dealflow.core.errors import AppError
    from dealflow.services.webhooks import WebhookService

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    service = WebhookService(session)
    with pytest.raises(AppError) as exc_info:
        await service.ingest(
            source_key="ghost",
            payload={},
            raw_body=b"{}",
            idempotency_key="k1",
        )
    assert exc_info.value.code == "source_not_found"


@pytest.mark.asyncio
async def test_webhook_service_returns_existing_on_duplicate() -> None:
    """Duplicate idempotency key returns the existing event without creating a new one."""
    from dealflow.db.models.lead_ingestion import IngestionEvent, LeadSource
    from dealflow.services.webhooks import WebhookService

    fake_source = MagicMock(spec=LeadSource)
    fake_source.secret_hash = None
    fake_source.tenant_id = uuid.uuid4()
    fake_source.id = uuid.uuid4()

    existing_event = MagicMock(spec=IngestionEvent)
    existing_event.id = uuid.uuid4()
    existing_event.status = "processed"

    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = fake_source

    event_result = MagicMock()
    event_result.scalar_one_or_none.return_value = existing_event

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[source_result, event_result])

    service = WebhookService(session)
    result = await service.ingest(
        source_key="my-source",
        payload={},
        raw_body=b"{}",
        idempotency_key="dup-key",
    )

    assert result is existing_event
    session.add.assert_not_called()  # no new rows created
