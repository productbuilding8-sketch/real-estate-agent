"""DAI-022: Timeline service — structured event logging for leads."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.errors import AppError
from dealflow.db.models.audit_knowledge import ActivityTimeline
from dealflow.db.models.lead_ingestion import Lead


class TimelineService:
    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "system",
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._actor_id = actor_id
        self._actor_type = actor_type

    def log(
        self,
        lead_id: uuid.UUID,
        event_type: str,
        event_data: dict[str, Any] | None = None,
        *,
        visible_to_agent: bool = True,
    ) -> ActivityTimeline:
        """Add a timeline entry to the session (synchronous — caller must flush/commit)."""
        entry = ActivityTimeline(
            tenant_id=self._tenant_id,
            lead_id=lead_id,
            event_type=event_type,
            event_data=event_data or {},
            actor_id=self._actor_id,
            actor_type=self._actor_type,
            visible_to_agent=visible_to_agent,
            occurred_at=datetime.now(tz=UTC),
        )
        self._session.add(entry)
        return entry

    async def add_note(self, lead_id: uuid.UUID, text: str) -> ActivityTimeline:
        """Add an agent note to a lead's timeline. Raises lead_not_found if the lead
        doesn't exist under this tenant."""
        result = await self._session.execute(
            sa.select(Lead).where(
                Lead.id == lead_id,
                Lead.tenant_id == self._tenant_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise AppError("lead_not_found", "Lead not found", 404)

        entry = self.log(lead_id, "lead.note_added", {"text": text})
        await self._session.flush()
        await self._session.commit()
        return entry
