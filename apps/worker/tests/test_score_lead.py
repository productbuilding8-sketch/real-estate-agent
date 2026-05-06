"""Tests for the lead scoring job."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.jobs.score_lead import JOB_NAME, compute_confidence_score, score_lead_job


# ── compute_confidence_score (pure function) ──────────────────────────────────


def test_full_profile_scores_1_0() -> None:
    """A lead with every signal set scores 1.0."""
    score = compute_confidence_score(
        has_email=True,
        has_phone=True,
        has_full_name=True,
        lead_type="buyer",
        has_budget=True,
        has_location=True,
    )
    assert score == 1.0


def test_empty_profile_scores_0_0() -> None:
    """A lead with no signals scores 0.0."""
    score = compute_confidence_score(
        has_email=False,
        has_phone=False,
        has_full_name=False,
        lead_type="unknown",
        has_budget=False,
        has_location=False,
    )
    assert score == 0.0


def test_email_only_scores_0_30() -> None:
    score = compute_confidence_score(
        has_email=True,
        has_phone=False,
        has_full_name=False,
        lead_type="unknown",
        has_budget=False,
        has_location=False,
    )
    assert score == 0.30


def test_email_and_phone_scores_0_50() -> None:
    score = compute_confidence_score(
        has_email=True,
        has_phone=True,
        has_full_name=False,
        lead_type="unknown",
        has_budget=False,
        has_location=False,
    )
    assert score == 0.50


def test_score_clamped_to_1_0() -> None:
    """Even if weights add up past 1.0, score is clamped."""
    score = compute_confidence_score(
        has_email=True,
        has_phone=True,
        has_full_name=True,
        lead_type="seller",
        has_budget=True,
        has_location=True,
    )
    assert score <= 1.0


def test_unknown_lead_type_does_not_add_weight() -> None:
    base = compute_confidence_score(
        has_email=True,
        has_phone=False,
        has_full_name=False,
        lead_type="unknown",
        has_budget=False,
        has_location=False,
    )
    with_type = compute_confidence_score(
        has_email=True,
        has_phone=False,
        has_full_name=False,
        lead_type="buyer",
        has_budget=False,
        has_location=False,
    )
    assert with_type > base
    assert round(with_type - base, 4) == 0.15


def test_job_name_constant() -> None:
    assert JOB_NAME == "score_lead_job"


# ── score_lead_job (async, mocked DB) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_job_returns_ok_and_score_on_success() -> None:
    """Job returns status=ok and the computed score when lead is found."""
    row = {
        "lead_type": "buyer",
        "first_name": "Jane",
        "last_name": "Doe",
        "has_email": True,
        "has_phone": True,
        "has_budget": False,
        "has_location": False,
    }
    mappings_mock = MagicMock()
    mappings_mock.one_or_none.return_value = row

    result_mock = MagicMock()
    result_mock.mappings.return_value = mappings_mock

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    session_maker = MagicMock(return_value=session)
    ctx = {"session_maker": session_maker}

    result = await score_lead_job(ctx, lead_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))

    assert result["status"] == "ok"
    # email(0.30) + phone(0.20) + full_name(0.20) + known_type(0.15) = 0.85
    assert result["score"] == 0.85
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_job_returns_skipped_when_lead_not_found() -> None:
    """Job returns status=skipped when the lead doesn't exist."""
    mappings_mock = MagicMock()
    mappings_mock.one_or_none.return_value = None

    result_mock = MagicMock()
    result_mock.mappings.return_value = mappings_mock

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    session_maker = MagicMock(return_value=session)
    ctx = {"session_maker": session_maker}

    result = await score_lead_job(ctx, lead_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))

    assert result["status"] == "skipped"
    assert result["reason"] == "lead_not_found"
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_job_writes_score_and_timeline() -> None:
    """Job calls UPDATE on leads and INSERT on activity_timeline."""
    row = {
        "lead_type": "seller",
        "first_name": "Bob",
        "last_name": None,  # partial name — no full_name bonus
        "has_email": True,
        "has_phone": False,
        "has_budget": True,
        "has_location": True,
    }
    mappings_mock = MagicMock()
    mappings_mock.one_or_none.return_value = row

    load_result = MagicMock()
    load_result.mappings.return_value = mappings_mock

    update_result = MagicMock()
    insert_result = MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[load_result, update_result, insert_result])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    session_maker = MagicMock(return_value=session)
    ctx = {"session_maker": session_maker}

    result = await score_lead_job(ctx, lead_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))

    assert result["status"] == "ok"
    # email(0.30) + known_type(0.15) + budget(0.10) + location(0.05) = 0.60
    assert result["score"] == 0.60
    assert session.execute.await_count == 3  # load + update + insert
