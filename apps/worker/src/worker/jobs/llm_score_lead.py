"""DAI-030: LLM-based lead qualification job using OpenAI.

Falls back to the heuristic score_lead_job when OpenAI is not configured.
Stores a structured qualification summary alongside the numeric score.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from worker.jobs.score_lead import compute_confidence_score
from worker.settings import get_settings

JOB_NAME = "llm_score_lead_job"

_LOAD_LEAD_SQL = sa.text(
    """
    SELECT
        l.lead_type,
        c.first_name,
        c.last_name,
        c.full_name,
        EXISTS(
            SELECT 1 FROM contact_points cp
            WHERE cp.contact_id = c.id AND cp.type = 'email'
        ) AS has_email,
        EXISTS(
            SELECT 1 FROM contact_points cp
            WHERE cp.contact_id = c.id AND cp.type = 'phone'
        ) AS has_phone,
        lp.budget_min,
        lp.budget_max,
        lp.location_city,
        lp.location_state,
        lp.property_types,
        lp.timeline,
        lp.financing_status,
        lp.purpose,
        (COALESCE(lp.budget_min, lp.budget_max) IS NOT NULL) AS has_budget,
        (lp.location_city IS NOT NULL) AS has_location
    FROM leads l
    JOIN contacts c ON c.id = l.contact_id
    LEFT JOIN lead_preferences lp ON lp.lead_id = l.id AND lp.tenant_id = :tenant_id
    WHERE l.id = :lead_id AND l.tenant_id = :tenant_id
    """
)

_UPDATE_SCORE_SQL = sa.text(
    "UPDATE leads SET confidence_score = :score, updated_at = :now "
    "WHERE id = :lead_id AND tenant_id = :tenant_id"
)

_INSERT_TIMELINE_SQL = sa.text(
    "INSERT INTO activity_timeline "
    "(id, tenant_id, lead_id, event_type, event_data, actor_type, visible_to_agent, occurred_at, created_at) "
    "VALUES (:id, :tenant_id, :lead_id, 'lead.scored', :event_data::jsonb, 'system', true, :now, :now)"
)

_SYSTEM_PROMPT = """\
You are a real estate lead qualification assistant.
Given structured lead data, output a JSON object with exactly these keys:
- "score": float 0.0–1.0 (qualification confidence)
- "tier": one of "hot" | "warm" | "cold"
- "summary": 1–2 sentence plain-English qualification rationale
- "flags": list of strings (concerns or positive signals, max 5)

Scoring guidelines:
- 0.8–1.0 (hot): clear intent, budget, timeline, contact info complete
- 0.5–0.79 (warm): partial info, some buying signals present
- 0.0–0.49 (cold): vague intent, missing contact info, no budget/timeline

Respond ONLY with valid JSON. No markdown, no extra text."""

_USER_TEMPLATE = """\
Lead type: {lead_type}
Name: {name}
Has email: {has_email}
Has phone: {has_phone}
Budget: {budget}
Location: {location}
Property types: {property_types}
Timeline: {timeline}
Financing status: {financing_status}
Purpose: {purpose}
"""


def _build_prompt(row: Any) -> str:
    budget_parts = []
    if row["budget_min"]:
        budget_parts.append(f"min ${row['budget_min']:,.0f}")
    if row["budget_max"]:
        budget_parts.append(f"max ${row['budget_max']:,.0f}")
    budget = ", ".join(budget_parts) or "unknown"

    loc_parts = [p for p in (row["location_city"], row["location_state"]) if p]
    location = ", ".join(loc_parts) or "unknown"

    prop_types = ", ".join(row["property_types"] or []) or "unknown"

    return _USER_TEMPLATE.format(
        lead_type=row["lead_type"] or "unknown",
        name=row["full_name"]
        or f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()
        or "unknown",
        has_email=row["has_email"],
        has_phone=row["has_phone"],
        budget=budget,
        location=location,
        property_types=prop_types,
        timeline=row["timeline"] or "unknown",
        financing_status=row["financing_status"] or "unknown",
        purpose=row["purpose"] or "unknown",
    )


def _call_openai(prompt: str) -> dict[str, Any]:
    """Call OpenAI chat completions. Returns parsed JSON dict."""
    settings = get_settings()
    # Import here so the module loads cleanly when openai is not installed
    from openai import OpenAI  # type: ignore[import-untyped]

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=300,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)  # type: ignore[no-any-return]


async def llm_score_lead_job(
    ctx: dict[str, Any],
    *,
    lead_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """ARQ job: qualify a lead with OpenAI, falling back to heuristic scoring.

    Returns dict with status, score, tier, summary, flags, and method.
    """
    settings = get_settings()
    session_maker = ctx["session_maker"]
    lid = uuid.UUID(lead_id)
    tid = uuid.UUID(tenant_id)

    async with session_maker() as session:
        row = (
            (await session.execute(_LOAD_LEAD_SQL, {"lead_id": lid, "tenant_id": tid}))
            .mappings()
            .one_or_none()
        )

        if row is None:
            return {"status": "skipped", "reason": "lead_not_found"}

        # Heuristic baseline (always computed)
        heuristic_score = compute_confidence_score(
            has_email=bool(row["has_email"]),
            has_phone=bool(row["has_phone"]),
            has_full_name=bool(
                (row["full_name"] or "").strip()
                or ((row["first_name"] or "") and (row["last_name"] or ""))
            ),
            lead_type=str(row["lead_type"] or ""),
            has_budget=bool(row["has_budget"]),
            has_location=bool(row["has_location"]),
        )

        method = "heuristic"
        score = heuristic_score
        tier: str = "cold" if score < 0.5 else ("warm" if score < 0.8 else "hot")
        summary: str = f"Heuristic score based on data completeness: {score:.0%}"
        flags: list[str] = []

        if settings.openai_api_key:
            try:
                prompt = _build_prompt(row)
                result = _call_openai(prompt)
                score = float(result.get("score", heuristic_score))
                score = round(min(max(score, 0.0), 1.0), 4)
                tier = result.get("tier", tier)
                summary = result.get("summary", summary)
                flags = result.get("flags", [])
                method = "llm"
            except Exception as exc:
                # LLM call failed — keep heuristic values, record the error in flags
                flags = [f"llm_error: {exc!s:.100}"]

        now = datetime.now(tz=UTC)
        await session.execute(
            _UPDATE_SCORE_SQL,
            {"score": score, "now": now, "lead_id": lid, "tenant_id": tid},
        )
        await session.execute(
            _INSERT_TIMELINE_SQL,
            {
                "id": uuid.uuid4(),
                "tenant_id": tid,
                "lead_id": lid,
                "event_data": json.dumps(
                    {
                        "score": score,
                        "tier": tier,
                        "summary": summary,
                        "flags": flags,
                        "method": method,
                    }
                ),
                "now": now,
            },
        )
        await session.commit()

    return {"status": "ok", "score": score, "tier": tier, "summary": summary, "method": method}
