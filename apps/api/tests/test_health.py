from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_version_returns_fields(client: AsyncClient) -> None:
    response = await client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.1.0"
    assert body["environment"] == "test"
    assert body["app_name"] == "DealFlow AI"


@pytest.mark.asyncio
async def test_404_returns_json_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_validation_error_returns_json(client: AsyncClient) -> None:
    response = await client.post("/api/v1/health", content="not-json")
    assert response.status_code in (404, 405, 422)
    body = response.json()
    assert "error" in body


@pytest.mark.asyncio
async def test_health_with_mocked_dependencies(client: AsyncClient) -> None:
    """Unit test — mocks DB and Redis so no real services needed."""
    with (
        patch(
            "dealflow.api.v1.routes.health._check_db",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "dealflow.api.v1.routes.health._check_redis",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert body["redis"] is True


@pytest.mark.asyncio
async def test_health_reports_db_down_gracefully(client: AsyncClient) -> None:
    """Health endpoint must not crash when DB is unreachable."""
    with (
        patch(
            "dealflow.api.v1.routes.health._check_db",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "dealflow.api.v1.routes.health._check_redis",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] is False
    assert body["redis"] is False


# ── Integration tests (require Docker: postgres + redis) ──────────────────────
@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_with_real_services(db_client: AsyncClient) -> None:
    response = await db_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["db"] is True
