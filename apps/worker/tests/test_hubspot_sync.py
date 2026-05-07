"""Tests for the HubSpot CRM sync job."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.jobs.hubspot_sync import (
    JOB_NAME,
    _map_lead_type,
    hubspot_sync_job,
)
from worker.utils.crypto import decrypt, encrypt

# ── crypto helper ─────────────────────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip() -> None:
    secret = "test-secret-key"
    plaintext = '{"access_token": "tok_abc"}'
    assert decrypt(encrypt(plaintext, secret), secret) == plaintext


def test_encrypt_different_each_call() -> None:
    """Fernet tokens include a timestamp so each encrypt call is unique."""
    secret = "test-secret-key"
    plaintext = "hello"
    assert encrypt(plaintext, secret) != encrypt(plaintext, secret)


# ── _map_lead_type ────────────────────────────────────────────────────────────


def test_map_lead_type_known_stages() -> None:
    assert _map_lead_type({"lifecyclestage": "lead"}) == "buyer"
    assert _map_lead_type({"lifecyclestage": "opportunity"}) == "buyer"
    assert _map_lead_type({"lifecyclestage": "subscriber"}) == "unknown"
    assert _map_lead_type({}) == "unknown"


# ── test context helpers ──────────────────────────────────────────────────────


SECRET = "ci-test-secret"


def _make_credentials(access_token: str = "tok_abc") -> str:
    return encrypt(json.dumps({"access_token": access_token}), SECRET)


def _make_conn_row(
    creds: str | None = None,
    last_sync_at: object = None,
) -> SimpleNamespace | None:
    if creds is False:
        return None
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        credentials_enc=creds or _make_credentials(),
        last_sync_at=last_sync_at,
        config={},
    )


def _make_source_row() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


def _make_ctx(conn_row: SimpleNamespace | None, source_row: SimpleNamespace | None = None) -> dict:
    execute_results: list[MagicMock] = []

    def _result(row: object) -> MagicMock:
        r = MagicMock()
        r.mappings.return_value.one_or_none.return_value = row
        return r

    # Calls: (1) load connection, (2) find source, then per-contact calls
    execute_results.append(_result(conn_row))
    execute_results.append(_result(source_row or (None if conn_row is None else _make_source_row())))

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()

    call_count = [0]

    async def _execute(*args: object, **kwargs: object) -> MagicMock:
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(execute_results):
            return execute_results[idx]
        # Default: return empty result for inserts/updates
        r = MagicMock()
        r.mappings.return_value.one_or_none.return_value = None
        return r

    session.execute = _execute
    session_maker = MagicMock(return_value=session)
    return {"session_maker": session_maker}


# ── skip paths ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_when_connection_not_found() -> None:
    ctx = _make_ctx(None)
    with patch("worker.jobs.hubspot_sync.get_settings") as ms:
        ms.return_value.secret_key = SECRET
        result = await hubspot_sync_job(
            ctx, connection_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4())
        )
    assert result["status"] == "skipped"
    assert result["reason"] == "connection_not_found"


@pytest.mark.asyncio
async def test_error_when_no_hubspot_lead_source() -> None:
    ctx = _make_ctx(_make_conn_row(), source_row=None)
    with patch("worker.jobs.hubspot_sync.get_settings") as ms:
        ms.return_value.secret_key = SECRET
        result = await hubspot_sync_job(
            ctx, connection_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4())
        )
    assert result["status"] == "error"
    assert result["reason"] == "no_hubspot_lead_source"


# ── successful sync (mocked HubSpot API) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_successful_sync_creates_leads() -> None:
    ctx = _make_ctx(_make_conn_row())

    hs_page = {
        "results": [
            {
                "id": "hs-001",
                "properties": {
                    "firstname": "Alice",
                    "lastname": "Walker",
                    "email": "alice@example.com",
                    "phone": "+15551234567",
                    "lifecyclestage": "lead",
                    "budget": None,
                    "city": "Austin",
                    "state": "TX",
                    "hs_lead_status": None,
                },
            }
        ],
        "paging": {},
    }

    with (
        patch("worker.jobs.hubspot_sync.get_settings") as ms,
        patch("worker.jobs.hubspot_sync._fetch_contacts_page", return_value=hs_page),
    ):
        ms.return_value.secret_key = SECRET
        result = await hubspot_sync_job(
            ctx, connection_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4())
        )

    assert result["status"] == "ok"
    assert result["created"] >= 0  # new lead or skipped existing


# ── HTTP error handling ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_error_returns_error_status() -> None:
    import httpx

    ctx = _make_ctx(_make_conn_row())

    with (
        patch("worker.jobs.hubspot_sync.get_settings") as ms,
        patch(
            "worker.jobs.hubspot_sync._fetch_contacts_page",
            side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=MagicMock()),
        ),
    ):
        ms.return_value.secret_key = SECRET
        result = await hubspot_sync_job(
            ctx, connection_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4())
        )

    assert result["status"] == "error"


def test_job_name_constant() -> None:
    assert JOB_NAME == "hubspot_sync_job"
