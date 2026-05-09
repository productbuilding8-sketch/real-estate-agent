"""DAI-018/019: Lead read service — list and detail queries."""

from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.api.v1.schemas.leads import (
    ContactDetail,
    ContactPointSchema,
    ContactSummary,
    LeadDetail,
    LeadListItem,
    LeadPreferenceSchema,
    SourceSummary,
    TimelineEventSchema,
)
from dealflow.db.models.audit_knowledge import ActivityTimeline
from dealflow.db.models.lead_ingestion import (
    Contact,
    ContactPoint,
    Lead,
    LeadPreference,
    LeadSource,
)
from dealflow.db.models.tenant_auth import User

_MAX_LIMIT = 100
_DEFAULT_LIMIT = 20
_TIMELINE_LIMIT = 50


def _full_name(first: str | None, last: str | None) -> str | None:
    parts = [p for p in [first, last] if p]
    return " ".join(parts) if parts else None


class LeadService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def list(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = _DEFAULT_LIMIT,
    ) -> tuple[list[LeadListItem], int]:
        """Return (items, total_count) for the given filters."""
        limit = min(limit, _MAX_LIMIT)
        offset = (page - 1) * limit

        # Subqueries to pull primary email / phone without exploding row count
        email_sq = (
            sa.select(ContactPoint.contact_id, ContactPoint.value_raw.label("email"))
            .where(
                ContactPoint.tenant_id == self._tenant_id,
                ContactPoint.type == "email",
                ContactPoint.is_primary.is_(True),
            )
            .subquery()
        )
        phone_sq = (
            sa.select(ContactPoint.contact_id, ContactPoint.value_raw.label("phone"))
            .where(
                ContactPoint.tenant_id == self._tenant_id,
                ContactPoint.type == "phone",
                ContactPoint.is_primary.is_(True),
            )
            .subquery()
        )

        base = (
            sa.select(Lead, Contact, LeadSource, email_sq.c.email, phone_sq.c.phone, User.name.label("agent_name"))
            .join(Contact, Lead.contact_id == Contact.id)
            .join(LeadSource, Lead.source_id == LeadSource.id)
            .outerjoin(email_sq, Contact.id == email_sq.c.contact_id)
            .outerjoin(phone_sq, Contact.id == phone_sq.c.contact_id)
            .outerjoin(User, Lead.assigned_agent_id == User.id)
            .where(Lead.tenant_id == self._tenant_id)
        )

        if status:
            base = base.where(Lead.status == status)
        if search:
            term = f"%{search}%"
            base = base.where(
                sa.or_(
                    Contact.first_name.ilike(term),
                    Contact.last_name.ilike(term),
                )
            )

        # Count (re-uses same filters; no pagination)
        count_q = (
            sa.select(sa.func.count(Lead.id))
            .select_from(Lead)
            .join(Contact, Lead.contact_id == Contact.id)
            .where(Lead.tenant_id == self._tenant_id)
        )
        if status:
            count_q = count_q.where(Lead.status == status)
        if search:
            term = f"%{search}%"
            count_q = count_q.where(
                sa.or_(
                    Contact.first_name.ilike(term),
                    Contact.last_name.ilike(term),
                )
            )
        total: int = (await self._session.execute(count_q)).scalar_one()

        rows_q = base.order_by(Lead.created_at.desc(), Lead.id).offset(offset).limit(limit)
        rows = (await self._session.execute(rows_q)).all()

        items = [
            LeadListItem(
                id=lead.id,
                status=lead.status,
                lead_type=lead.lead_type,
                confidence_score=lead.confidence_score,
                assigned_agent_id=lead.assigned_agent_id,
                assigned_agent_name=agent_name,
                created_at=lead.created_at,
                last_activity_at=lead.last_activity_at,
                contact=ContactSummary(
                    id=contact.id,
                    full_name=_full_name(contact.first_name, contact.last_name),
                    email=email,
                    phone=phone,
                ),
                source=SourceSummary(id=source.id, name=source.name, type=source.type),
            )
            for lead, contact, source, email, phone, agent_name in rows
        ]
        return items, total

    async def status_counts(self, *, search: str | None = None) -> dict[str, int]:
        """Return total lead counts grouped by status for the tenant.

        Search filter is respected; status filter is intentionally omitted so
        all tabs show accurate totals regardless of the active filter.
        """
        q = (
            sa.select(Lead.status, sa.func.count(Lead.id).label("cnt"))
            .join(Contact, Lead.contact_id == Contact.id)
            .where(Lead.tenant_id == self._tenant_id)
            .group_by(Lead.status)
        )
        if search:
            term = f"%{search}%"
            q = q.where(
                sa.or_(
                    Contact.first_name.ilike(term),
                    Contact.last_name.ilike(term),
                )
            )
        rows = (await self._session.execute(q)).all()
        return {row.status: row.cnt for row in rows}

    async def get_detail(self, lead_id: uuid.UUID) -> LeadDetail | None:
        """Return full lead detail, or None if not found / wrong tenant."""
        row_q = (
            sa.select(Lead, Contact, LeadSource)
            .join(Contact, Lead.contact_id == Contact.id)
            .join(LeadSource, Lead.source_id == LeadSource.id)
            .where(Lead.id == lead_id, Lead.tenant_id == self._tenant_id)
        )
        row = (await self._session.execute(row_q)).one_or_none()
        if row is None:
            return None

        lead, contact, source = row

        # Contact points
        cp_rows = (
            (
                await self._session.execute(
                    sa.select(ContactPoint)
                    .where(
                        ContactPoint.contact_id == contact.id,
                        ContactPoint.tenant_id == self._tenant_id,
                    )
                    .order_by(ContactPoint.is_primary.desc(), ContactPoint.type)
                )
            )
            .scalars()
            .all()
        )

        def _primary(type_: str) -> str | None:
            for cp in cp_rows:
                if cp.type == type_ and cp.is_primary:
                    return cp.value_raw
            return next((cp.value_raw for cp in cp_rows if cp.type == type_), None)

        # Preferences (optional 1-1)
        preference: Any = (
            await self._session.execute(
                sa.select(LeadPreference).where(
                    LeadPreference.lead_id == lead_id,
                    LeadPreference.tenant_id == self._tenant_id,
                )
            )
        ).scalar_one_or_none()

        # Timeline (most recent first, agent-visible only)
        timeline_rows = (
            (
                await self._session.execute(
                    sa.select(ActivityTimeline)
                    .where(
                        ActivityTimeline.lead_id == lead_id,
                        ActivityTimeline.tenant_id == self._tenant_id,
                        ActivityTimeline.visible_to_agent.is_(True),
                    )
                    .order_by(ActivityTimeline.occurred_at.desc())
                    .limit(_TIMELINE_LIMIT)
                )
            )
            .scalars()
            .all()
        )

        return LeadDetail(
            id=lead.id,
            status=lead.status,
            lead_type=lead.lead_type,
            confidence_score=lead.confidence_score,
            assigned_agent_id=lead.assigned_agent_id,
            created_at=lead.created_at,
            last_activity_at=lead.last_activity_at,
            first_response_at=lead.first_response_at,
            stale_at=lead.stale_at,
            raw_payload=lead.raw_payload,
            contact=ContactDetail(
                id=contact.id,
                full_name=_full_name(contact.first_name, contact.last_name),
                email=_primary("email"),
                phone=_primary("phone"),
                contact_points=[
                    ContactPointSchema(
                        type=cp.type,
                        value=cp.value_raw,
                        is_primary=cp.is_primary,
                    )
                    for cp in cp_rows
                ],
            ),
            source=SourceSummary(id=source.id, name=source.name, type=source.type),
            preferences=(LeadPreferenceSchema.model_validate(preference) if preference else None),
            timeline=[
                TimelineEventSchema(
                    id=event.id,
                    event_type=event.event_type,
                    event_data=event.event_data,
                    actor_type=event.actor_type,
                    occurred_at=event.occurred_at,
                )
                for event in timeline_rows
            ],
        )
