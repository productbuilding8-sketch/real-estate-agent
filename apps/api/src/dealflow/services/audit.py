"""DAI-058: Audit log service — writes to audit_logs and activity_timeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.db.models.audit_knowledge import ActivityTimeline, AuditLog


class AuditService:
    """Writes compliance audit entries and lead activity timeline events.

    All writes go into the caller's session — they commit (or roll back) together
    with the business operation that triggered them. This ensures audit entries
    are never missing when a business record exists, and never exist when the
    business record was rolled back.

    Usage::

        audit = AuditService(session, tenant_id=ctx.tenant_id)
        await audit.log(
            action="lead.created",
            entity_type="lead",
            entity_id=lead.id,
            after={"status": "new", "contact_id": str(lead.contact_id)},
            actor_id=ctx.user_id,
            actor_type="user",
        )
    """

    def __init__(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def log(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "system",
        ip_address: str | None = None,
    ) -> AuditLog:
        """Append an audit log entry.

        `before` / `after` are the entity state snapshots. The PII scrubbing
        worker reads rows where `pii_fields_scrubbed = false` and redacts
        sensitive fields within 1 hour of creation.
        """
        entry = AuditLog(
            tenant_id=self._tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before,
            after_state=after,
            ip_address=ip_address,
            pii_fields_scrubbed=False,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def add_timeline_event(
        self,
        *,
        lead_id: uuid.UUID,
        event_type: str,
        event_data: dict[str, Any] | None = None,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "system",
        visible_to_agent: bool = True,
        occurred_at: datetime | None = None,
    ) -> ActivityTimeline:
        """Append a timeline event for the lead detail activity feed."""
        event = ActivityTimeline(
            tenant_id=self._tenant_id,
            lead_id=lead_id,
            event_type=event_type,
            event_data=event_data,
            actor_id=actor_id,
            actor_type=actor_type,
            visible_to_agent=visible_to_agent,
            occurred_at=occurred_at or datetime.now(tz=timezone.utc),
        )
        self._session.add(event)
        await self._session.flush()
        return event
