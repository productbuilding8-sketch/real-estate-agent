"""Tests for the outbound email job."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.jobs.send_email import JOB_NAME, send_email_job


@pytest.fixture()
def ctx() -> dict:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session_maker = MagicMock(return_value=session)
    return {"session_maker": session_maker, "_session": session}


def _make_execute_result(email: str | None):
    row = {"email": email} if email is not None else None
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    return AsyncMock(return_value=result)


# ── skip when SMTP not configured ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_when_smtp_not_configured(ctx: dict) -> None:
    with patch("worker.jobs.send_email.get_settings") as mock_settings:
        mock_settings.return_value.smtp_host = None
        result = await send_email_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            subject="Hello",
            body="Test body",
        )
    assert result["status"] == "skipped"
    assert result["reason"] == "smtp_not_configured"


# ── skip when lead has no primary email ──────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_when_no_primary_email(ctx: dict) -> None:
    ctx["_session"].execute = _make_execute_result(None)

    with patch("worker.jobs.send_email.get_settings") as mock_settings:
        mock_settings.return_value.smtp_host = "smtp.example.com"
        mock_settings.return_value.smtp_port = 587
        mock_settings.return_value.smtp_user = "user@example.com"
        mock_settings.return_value.smtp_password = "secret"
        mock_settings.return_value.smtp_from_address = "noreply@dealflow.ai"
        mock_settings.return_value.smtp_from_name = "DealFlow AI"
        result = await send_email_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            subject="Hello",
            body="Test body",
        )
    assert result["status"] == "skipped"
    assert result["reason"] == "no_primary_email"


# ── success path ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sends_email_and_records_timeline(ctx: dict) -> None:
    email_addr = "lead@example.com"

    ctx["_session"].execute = AsyncMock(
        side_effect=[
            _make_execute_result(email_addr).return_value,
            AsyncMock(),
        ]
    )

    with (
        patch("worker.jobs.send_email.get_settings") as mock_settings,
        patch("worker.jobs.send_email._send_smtp_email") as mock_send,
    ):
        mock_settings.return_value.smtp_host = "smtp.example.com"
        mock_settings.return_value.smtp_port = 587
        mock_settings.return_value.smtp_user = "user@example.com"
        mock_settings.return_value.smtp_password = "secret"
        mock_settings.return_value.smtp_from_address = "noreply@dealflow.ai"
        mock_settings.return_value.smtp_from_name = "DealFlow AI"

        result = await send_email_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            subject="Welcome to DealFlow",
            body="Hi there, let's connect.",
        )

    assert result["status"] == "ok"
    assert result["to"] == email_addr
    mock_send.assert_called_once_with(email_addr, "Welcome to DealFlow", "Hi there, let's connect.")


# ── SMTP error is returned, not raised ───────────────────────────────────────


@pytest.mark.asyncio
async def test_smtp_error_returned_as_error_status(ctx: dict) -> None:
    email_addr = "lead@example.com"
    ctx["_session"].execute = AsyncMock(return_value=_make_execute_result(email_addr).return_value)

    with (
        patch("worker.jobs.send_email.get_settings") as mock_settings,
        patch("worker.jobs.send_email._send_smtp_email", side_effect=RuntimeError("connection refused")),
    ):
        mock_settings.return_value.smtp_host = "smtp.example.com"
        mock_settings.return_value.smtp_port = 587
        mock_settings.return_value.smtp_user = "user@example.com"
        mock_settings.return_value.smtp_password = "secret"
        mock_settings.return_value.smtp_from_address = "noreply@dealflow.ai"
        mock_settings.return_value.smtp_from_name = "DealFlow AI"

        result = await send_email_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            subject="Hello",
            body="Body",
        )

    assert result["status"] == "error"
    assert "connection refused" in result["reason"]


def test_job_name_constant() -> None:
    assert JOB_NAME == "send_email_job"
