"""DAI-021: Lead mutation service — status transitions and agent assignment."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.errors import AppError
from dealflow.db.models.audit_knowledge import ActivityTimeline
from dealflow.db.models.lead_ingestion import Lead

# Valid status transitions: key → allowed next statuses
TRANSITIONS: dict[str, frozenset[str]] = {
    "new": frozenset({"contacted", "qualified", "lost", "archived"}),
    "contacted": frozenset({"qualified", "lost", "archived"}),
    "qualified": frozenset({"converted", "lost", "archived"}),
    "converted": frozenset({"archived"}),
    "lost": frozenset({"new", "archived"}),
    "archived": frozenset(),
}
ALL_STATUSES: frozenset[str] = frozenset(TRANSITIONS.keys())


class LeadMutationService:
    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._actor_id = actor_id

    async def update_status(
        self,
        lead_id: uuid.UUID,
        new_status: str,
        reason: str | None = None,
    ) -> Lead:
        """Transition a lead to a new status, enforcing the state machine."""
        if new_status not in ALL_STATUSES:
            raise AppError(
                "invalid_status",
                f"'{new_status}' is not a recognised lead status",
                422,
            )
        lead = await self._load(lead_id)
        allowed = TRANSITIONS.get(lead.status, frozenset())
        if new_status not in allowed:
            raise AppError(
                "invalid_transition",
                f"Cannot transition from '{lead.status}' to '{new_status}'",
                409,
            )
        old_status = lead.status
        now = datetime.now(tz=UTC)
        lead.status = new_status
        lead.last_activity_at = now

        event_data: dict[str, Any] = {"from": old_status, "to": new_status}
        if reason:
            event_data["reason"] = reason
        await self._log(lead_id, "lead.status_changed", event_data)

        await self._session.flush()
        await self._session.commit()
        return lead

    async def assign(
        self,
        lead_id: uuid.UUID,
        agent_id: uuid.UUID | None,
    ) -> Lead:
        """Assign or unassign a lead. Pass agent_id=None to unassign."""
        lead = await self._load(lead_id)
        old_agent = lead.assigned_agent_id
        now = datetime.now(tz=UTC)
        lead.assigned_agent_id = agent_id
        lead.last_activity_at = now

        event_type = "lead.assigned" if agent_id else "lead.unassigned"
        event_data: dict[str, Any] = {
            "agent_id": str(agent_id) if agent_id else None,
            "previous_agent_id": str(old_agent) if old_agent else None,
        }
        await self._log(lead_id, event_type, event_data)

        await self._session.flush()
        await self._session.commit()
        return lead

    # ── private helpers ───────────────────────────────────────────────────────

    async def _load(self, lead_id: uuid.UUID) -> Lead:
        result = await self._session.execute(
            sa.select(Lead).where(
                Lead.id == lead_id,
                Lead.tenant_id == self._tenant_id,
            )
        )
        lead = result.scalar_one_or_none()
        if lead is None:
            raise AppError("lead_not_found", "Lead not found", 404)
        return lead

    async def _log(
        self,
        lead_id: uuid.UUID,
        event_type: str,
        event_data: dict[str, Any],
    ) -> None:
        self._session.add(
            ActivityTimeline(
                tenant_id=self._tenant_id,
                lead_id=lead_id,
                event_type=event_type,
                event_data=event_data,
                actor_id=self._actor_id,
                actor_type="user",
                visible_to_agent=True,
                occurred_at=datetime.now(tz=UTC),
            )
        )
