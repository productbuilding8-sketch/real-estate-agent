"""Tests for the LLM lead qualification job."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.jobs.llm_score_lead import JOB_NAME, _build_prompt, llm_score_lead_job

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_row(**overrides: object) -> SimpleNamespace:
    defaults = dict(
        lead_type="buyer",
        first_name="Jane",
        last_name="Smith",
        full_name="Jane Smith",
        has_email=True,
        has_phone=True,
        budget_min=400_000,
        budget_max=600_000,
        location_city="Austin",
        location_state="TX",
        property_types=["single_family"],
        timeline="3-6 months",
        financing_status="pre-approved",
        purpose="primary_residence",
        has_budget=True,
        has_location=True,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_ctx(row: SimpleNamespace | None) -> dict:
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session_maker = MagicMock(return_value=session)
    return {"session_maker": session_maker}


# ── _build_prompt ──────────────────────────────────────────────────────────────


def test_build_prompt_includes_lead_type() -> None:
    row = _make_row()
    prompt = _build_prompt(row)
    assert "buyer" in prompt
    assert "Jane Smith" in prompt
    assert "Austin, TX" in prompt
    assert "$400,000" in prompt


def test_build_prompt_handles_missing_fields() -> None:
    row = _make_row(
        full_name=None, first_name=None, last_name=None,
        budget_min=None, budget_max=None,
        location_city=None, location_state=None,
        property_types=None, timeline=None,
        financing_status=None, purpose=None,
    )
    prompt = _build_prompt(row)
    assert "unknown" in prompt


# ── lead not found ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_when_lead_not_found() -> None:
    ctx = _make_ctx(None)
    result = await llm_score_lead_job(
        ctx,
        lead_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
    )
    assert result["status"] == "skipped"
    assert result["reason"] == "lead_not_found"


# ── heuristic fallback (no OpenAI key) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_heuristic_when_openai_not_configured() -> None:
    ctx = _make_ctx(_make_row())
    with patch("worker.jobs.llm_score_lead.get_settings") as mock_settings:
        mock_settings.return_value.openai_api_key = None
        result = await llm_score_lead_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
        )
    assert result["status"] == "ok"
    assert result["method"] == "heuristic"
    assert 0.0 <= result["score"] <= 1.0
    assert result["tier"] in ("hot", "warm", "cold")


# ── LLM success path ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_score_used_when_openai_configured() -> None:
    ctx = _make_ctx(_make_row())
    llm_response = {
        "score": 0.91,
        "tier": "hot",
        "summary": "Pre-approved buyer with clear budget and timeline.",
        "flags": ["pre_approved", "motivated"],
    }
    with (
        patch("worker.jobs.llm_score_lead.get_settings") as mock_settings,
        patch("worker.jobs.llm_score_lead._call_openai", return_value=llm_response),
    ):
        mock_settings.return_value.openai_api_key = "sk-fake"
        mock_settings.return_value.openai_model = "gpt-4o-mini"
        result = await llm_score_lead_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
        )
    assert result["status"] == "ok"
    assert result["method"] == "llm"
    assert result["score"] == 0.91
    assert result["tier"] == "hot"
    assert "Pre-approved" in result["summary"]


# ── LLM error falls back to heuristic ────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_error_falls_back_to_heuristic() -> None:
    ctx = _make_ctx(_make_row())
    with (
        patch("worker.jobs.llm_score_lead.get_settings") as mock_settings,
        patch("worker.jobs.llm_score_lead._call_openai", side_effect=RuntimeError("timeout")),
    ):
        mock_settings.return_value.openai_api_key = "sk-fake"
        mock_settings.return_value.openai_model = "gpt-4o-mini"
        result = await llm_score_lead_job(
            ctx,
            lead_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
        )
    assert result["status"] == "ok"
    assert result["method"] == "heuristic"
    assert 0.0 <= result["score"] <= 1.0


def test_job_name_constant() -> None:
    assert JOB_NAME == "llm_score_lead_job"
