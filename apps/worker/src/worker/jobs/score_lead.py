"""DAI-023: Lead scoring job — computes a confidence_score from contact completeness."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

JOB_NAME = "score_lead_job"

# Weight table (must sum to 1.0)
_WEIGHTS = {
    "has_email": 0.30,
    "has_phone": 0.20,
    "has_full_name": 0.20,
    "known_lead_type": 0.15,
    "has_budget": 0.10,
    "has_location": 0.05,
}

_LOAD_SQL = sa.text(
    """
    SELECT
        l.lead_type,
        c.first_name,
        c.last_name,
        EXISTS(
            SELECT 1 FROM contact_points cp
            WHERE cp.contact_id = c.id AND cp.type = 'email'
        ) AS has_email,
        EXISTS(
            SELECT 1 FROM contact_points cp
            WHERE cp.contact_id = c.id AND cp.type = 'phone'
        ) AS has_phone,
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


def compute_confidence_score(
    *,
    has_email: bool,
    has_phone: bool,
    has_full_name: bool,
    lead_type: str,
    has_budget: bool,
    has_location: bool,
) -> float:
    """Return a 0.0–1.0 confidence score based on data completeness signals."""
    score = 0.0
    if has_email:
        score += _WEIGHTS["has_email"]
    if has_phone:
        score += _WEIGHTS["has_phone"]
    if has_full_name:
        score += _WEIGHTS["has_full_name"]
    if lead_type and lead_type != "unknown":
        score += _WEIGHTS["known_lead_type"]
    if has_budget:
        score += _WEIGHTS["has_budget"]
    if has_location:
        score += _WEIGHTS["has_location"]
    return round(min(score, 1.0), 4)


async def score_lead_job(
    ctx: dict[str, Any],
    *,
    lead_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """ARQ job: compute and persist a confidence score for one lead."""
    session_maker = ctx["session_maker"]
    lid = uuid.UUID(lead_id)
    tid = uuid.UUID(tenant_id)

    async with session_maker() as session:
        row = (
            (await session.execute(_LOAD_SQL, {"lead_id": lid, "tenant_id": tid}))
            .mappings()
            .one_or_none()
        )

        if row is None:
            return {"status": "skipped", "reason": "lead_not_found"}

        score = compute_confidence_score(
            has_email=bool(row["has_email"]),
            has_phone=bool(row["has_phone"]),
            has_full_name=bool(row["first_name"] and row["last_name"]),
            lead_type=str(row["lead_type"]),
            has_budget=bool(row["has_budget"]),
            has_location=bool(row["has_location"]),
        )

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
                "event_data": json.dumps({"score": score}),
                "now": now,
            },
        )
        await session.commit()

    return {"status": "ok", "score": score}
