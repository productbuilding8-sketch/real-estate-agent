"""Tests for the transactional outbox poller (DAI-039)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from worker.jobs.poll_outbox import MAX_RETRIES, _BACKOFF, poll_outbox_job


def _make_ctx(rows: list[dict[str, Any]], claim_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a minimal ARQ ctx mock."""
    # session.execute returns a result whose .mappings().all() gives rows
    list_result = MagicMock()
    list_result.mappings.return_value.all.return_value = rows

    # claim returns one row (or None if already claimed)
    claim_result_mock = MagicMock()
    claim_result_mock.mappings.return_value.one_or_none.return_value = claim_result

    execute_mock = AsyncMock(side_effect=[
        MagicMock(),          # _RECOVER_STALE_SQL (first session)
        list_result,          # _LIST_PENDING_SQL (second session)
    ] + [claim_result_mock, MagicMock()] * len(rows))  # claim + mark per row

    session = AsyncMock()
    session.execute = execute_mock
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    session_maker = MagicMock(return_value=session)

    redis = AsyncMock()

    return {"session_maker": session_maker, "redis": redis, "_session": session}


# ── No pending events ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_outbox_returns_zero_counts() -> None:
    ctx = _make_ctx(rows=[])
    result = await poll_outbox_job(ctx)
    assert result == {"status": "ok", "dispatched": 0, "retried": 0, "dead": 0}
    ctx["redis"].enqueue_job.assert_not_called()


# ── Successful dispatch ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_known_event_type_is_dispatched() -> None:
    event_id = uuid.uuid4()
    rows = [
        {
            "id": event_id,
            "event_type": "lead.sms.requested",
            "payload": {"lead_id": "abc", "tenant_id": "xyz", "message": "hi"},
            "attempts": 0,
        }
    ]
    ctx = _make_ctx(rows=rows, claim_result={"attempts": 1})

    result = await poll_outbox_job(ctx)

    assert result["dispatched"] == 1
    assert result["retried"] == 0
    assert result["dead"] == 0
    ctx["redis"].enqueue_job.assert_called_once_with(
        "send_sms_job",
        _queue_name="dealflow:jobs",
        lead_id="abc",
        tenant_id="xyz",
        message="hi",
    )


# ── Unknown event type → retry ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_event_type_is_retried() -> None:
    rows = [
        {
            "id": uuid.uuid4(),
            "event_type": "unknown.event",
            "payload": {},
            "attempts": 0,
        }
    ]
    ctx = _make_ctx(rows=rows, claim_result={"attempts": 1})

    result = await poll_outbox_job(ctx)

    assert result["dispatched"] == 0
    assert result["retried"] == 1
    assert result["dead"] == 0
    ctx["redis"].enqueue_job.assert_not_called()


# ── Dead-letter after MAX_RETRIES ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exhausted_retries_become_dead() -> None:
    rows = [
        {
            "id": uuid.uuid4(),
            "event_type": "unknown.event",
            "payload": {},
            "attempts": 0,
        }
    ]
    ctx = _make_ctx(rows=rows, claim_result={"attempts": MAX_RETRIES})

    result = await poll_outbox_job(ctx)

    assert result["dead"] == 1
    assert result["retried"] == 0


# ── Skipped when already claimed ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_already_claimed_row_is_skipped() -> None:
    rows = [
        {
            "id": uuid.uuid4(),
            "event_type": "lead.score.requested",
            "payload": {"lead_id": "a", "tenant_id": "b"},
            "attempts": 0,
        }
    ]
    ctx = _make_ctx(rows=rows, claim_result=None)  # None = another worker claimed it

    result = await poll_outbox_job(ctx)

    assert result["dispatched"] == 0
    ctx["redis"].enqueue_job.assert_not_called()


# ── Back-off delay grows with attempts ───────────────────────────────────────


def test_backoff_sequence_matches_spec() -> None:
    assert _BACKOFF[0] == 30      # 30 s
    assert _BACKOFF[1] == 120     # 2 min
    assert _BACKOFF[2] == 480     # 8 min
    assert _BACKOFF[3] == 1800    # 30 min
    assert _BACKOFF[4] == 7200    # 2 h


# ── Event type → job name mapping ────────────────────────────────────────────


def test_all_dispatch_targets_are_registered() -> None:
    from worker.jobs.poll_outbox import _DISPATCH

    assert _DISPATCH["lead.sms.requested"] == "send_sms_job"
    assert _DISPATCH["lead.email.requested"] == "send_email_job"
    assert _DISPATCH["lead.score.requested"] == "llm_score_lead_job"
    assert _DISPATCH["integration.hubspot.sync"] == "hubspot_sync_job"
