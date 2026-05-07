"""DAI-029: Outbound SMS job — sends a templated SMS to a lead via Twilio."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from worker.settings import get_settings

JOB_NAME = "send_sms_job"

_LOAD_PHONE_SQL = sa.text(
    """
    SELECT cp.value AS phone
    FROM leads l
    JOIN contacts c ON c.id = l.contact_id
    JOIN contact_points cp ON cp.contact_id = c.id
    WHERE l.id = :lead_id
      AND l.tenant_id = :tenant_id
      AND cp.type = 'phone'
      AND cp.is_primary = true
    LIMIT 1
    """
)

_INSERT_TIMELINE_SQL = sa.text(
    "INSERT INTO activity_timeline "
    "(id, tenant_id, lead_id, event_type, event_data, actor_type, visible_to_agent, occurred_at, created_at) "
    "VALUES (:id, :tenant_id, :lead_id, 'sms.sent', :event_data::jsonb, 'system', true, :now, :now)"
)


def _send_twilio_sms(to: str, body: str) -> str:
    """Send an SMS via Twilio REST API. Returns the SID."""
    settings = get_settings()
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number):
        raise RuntimeError("Twilio credentials not configured")

    # Import here so the job module loads even without twilio installed in dev
    from twilio.rest import Client  # type: ignore[import-untyped]

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    message = client.messages.create(
        body=body,
        from_=settings.twilio_from_number,
        to=to,
    )
    return str(message.sid)


async def send_sms_job(
    ctx: dict[str, Any],
    *,
    lead_id: str,
    tenant_id: str,
    message: str,
) -> dict[str, Any]:
    """ARQ job: send an outbound SMS to a lead's primary phone number.

    Skips silently if Twilio is not configured (dev/test environments).
    Records an activity_timeline event on success.
    """
    settings = get_settings()
    if not settings.twilio_account_sid:
        return {"status": "skipped", "reason": "twilio_not_configured"}

    session_maker = ctx["session_maker"]
    lid = uuid.UUID(lead_id)
    tid = uuid.UUID(tenant_id)

    async with session_maker() as session:
        row = (
            await session.execute(_LOAD_PHONE_SQL, {"lead_id": lid, "tenant_id": tid})
        ).mappings().one_or_none()

        if row is None:
            return {"status": "skipped", "reason": "no_primary_phone"}

        phone: str = row["phone"]

    # Twilio call is synchronous — run it outside the DB session to avoid holding the connection
    try:
        sid = _send_twilio_sms(phone, message)
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}

    now = datetime.now(tz=UTC)
    async with session_maker() as session:
        await session.execute(
            _INSERT_TIMELINE_SQL,
            {
                "id": uuid.uuid4(),
                "tenant_id": tid,
                "lead_id": lid,
                "event_data": json.dumps({"to": phone, "sid": sid, "preview": message[:60]}),
                "now": now,
            },
        )
        await session.commit()

    return {"status": "ok", "sid": sid, "to": phone}
