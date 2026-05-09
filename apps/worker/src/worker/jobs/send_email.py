"""DAI-034: Outbound email job — sends an email to a lead via SMTP."""

from __future__ import annotations

import json
import smtplib
import uuid
from datetime import UTC, datetime
from email.mime.text import MIMEText
from typing import Any

import sqlalchemy as sa

from worker.settings import get_settings

JOB_NAME = "send_email_job"

_LOAD_EMAIL_SQL = sa.text(
    """
    SELECT cp.value AS email
    FROM leads l
    JOIN contacts c ON c.id = l.contact_id
    JOIN contact_points cp ON cp.contact_id = c.id
    WHERE l.id = :lead_id
      AND l.tenant_id = :tenant_id
      AND cp.type = 'email'
      AND cp.is_primary = true
    LIMIT 1
    """
)

_INSERT_TIMELINE_SQL = sa.text(
    "INSERT INTO activity_timeline "
    "(id, tenant_id, lead_id, event_type, event_data, actor_type, visible_to_agent, occurred_at, created_at) "
    "VALUES (:id, :tenant_id, :lead_id, 'email.sent', :event_data::jsonb, 'system', true, :now, :now)"
)


def _send_smtp_email(to: str, subject: str, body: str) -> None:
    """Send an email via SMTP. Raises on failure."""
    settings = get_settings()
    if not (
        settings.smtp_host
        and settings.smtp_user
        and settings.smtp_password
        and settings.smtp_from_address
    ):
        raise RuntimeError("SMTP credentials not configured")

    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
    msg["To"] = to

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from_address, [to], msg.as_string())


async def send_email_job(
    ctx: dict[str, Any],
    *,
    lead_id: str,
    tenant_id: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """ARQ job: send an outbound email to a lead's primary email address.

    Skips silently if SMTP is not configured (dev/test environments).
    Records an activity_timeline event on success.
    """
    settings = get_settings()
    if not settings.smtp_host:
        return {"status": "skipped", "reason": "smtp_not_configured"}

    session_maker = ctx["session_maker"]
    lid = uuid.UUID(lead_id)
    tid = uuid.UUID(tenant_id)

    async with session_maker() as session:
        row = (
            (await session.execute(_LOAD_EMAIL_SQL, {"lead_id": lid, "tenant_id": tid}))
            .mappings()
            .one_or_none()
        )

        if row is None:
            return {"status": "skipped", "reason": "no_primary_email"}

        email_address: str = row["email"]

    try:
        _send_smtp_email(email_address, subject, body)
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
                "event_data": json.dumps(
                    {
                        "to": email_address,
                        "subject": subject,
                        "preview": body[:60],
                    }
                ),
                "now": now,
            },
        )
        await session.commit()

    return {"status": "ok", "to": email_address}
