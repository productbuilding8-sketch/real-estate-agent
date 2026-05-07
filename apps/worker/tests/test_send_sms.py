"""Tests for the outbound SMS job."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.jobs.send_sms import JOB_NAME, send_sms_job


@pytest.fixture()
def ctx() -> dict:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session_maker = MagicMock(return_value=session)
    return {"session_maker": session_maker, "_session": session}


def _make_execute_result(phone: str | None):
    row = SimpleNamespace(phone=phone) if phone else None
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    return AsyncMock(return_value=result)


# ── skip when Twilio not configured ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_when_twilio_not_configured(ctx: dict) -> None:
    with patch("worker.jobs.send_sms.get_settings") as mock_settings:
        mock_settings.return_value.twilio_account_sid = None
        result = await send_sms_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            message="Hello!",
        )
    assert result["status"] == "skipped"
    assert result["reason"] == "twilio_not_configured"


# ── skip when lead has no primary phone ──────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_when_no_primary_phone(ctx: dict) -> None:
    ctx["_session"].execute = _make_execute_result(None)

    with patch("worker.jobs.send_sms.get_settings") as mock_settings:
        mock_settings.return_value.twilio_account_sid = "ACfake"
        mock_settings.return_value.twilio_auth_token = "token"
        mock_settings.return_value.twilio_from_number = "+15550001111"
        result = await send_sms_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            message="Hello!",
        )
    assert result["status"] == "skipped"
    assert result["reason"] == "no_primary_phone"


# ── success path ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sends_sms_and_records_timeline(ctx: dict) -> None:
    phone = "+15559876543"
    fake_sid = "SM123abc"

    # First execute call: load phone. Second: insert timeline.
    ctx["_session"].execute = AsyncMock(
        side_effect=[
            _make_execute_result(phone).return_value,
            AsyncMock(),
        ]
    )

    with (
        patch("worker.jobs.send_sms.get_settings") as mock_settings,
        patch("worker.jobs.send_sms._send_twilio_sms", return_value=fake_sid) as mock_send,
    ):
        mock_settings.return_value.twilio_account_sid = "ACfake"
        mock_settings.return_value.twilio_auth_token = "token"
        mock_settings.return_value.twilio_from_number = "+15550001111"

        result = await send_sms_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            message="Welcome to DealFlow!",
        )

    assert result["status"] == "ok"
    assert result["sid"] == fake_sid
    assert result["to"] == phone
    mock_send.assert_called_once_with(phone, "Welcome to DealFlow!")


# ── Twilio error is returned, not raised ─────────────────────────────────────


@pytest.mark.asyncio
async def test_twilio_error_returned_as_error_status(ctx: dict) -> None:
    phone = "+15559876543"
    ctx["_session"].execute = AsyncMock(return_value=_make_execute_result(phone).return_value)

    with (
        patch("worker.jobs.send_sms.get_settings") as mock_settings,
        patch("worker.jobs.send_sms._send_twilio_sms", side_effect=RuntimeError("auth error")),
    ):
        mock_settings.return_value.twilio_account_sid = "ACfake"
        mock_settings.return_value.twilio_auth_token = "token"
        mock_settings.return_value.twilio_from_number = "+15550001111"

        result = await send_sms_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            message="Hello",
        )

    assert result["status"] == "error"
    assert "auth error" in result["reason"]


def test_job_name_constant() -> None:
    assert JOB_NAME == "send_sms_job"
