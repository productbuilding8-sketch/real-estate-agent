"""DAI-020: Webhook ingestion service — receives leads from external sources."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.errors import AppError
from dealflow.db.models.lead_ingestion import (
    Contact,
    ContactPoint,
    IngestionEvent,
    Lead,
    LeadSource,
)
from dealflow.services.timeline import TimelineService

_SUPPORTED_EVENT_TYPE = "lead.webhook"


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ingest(
        self,
        *,
        source_key: str,
        payload: dict[str, Any],
        raw_body: bytes,
        idempotency_key: str,
        signature: str | None = None,
    ) -> IngestionEvent:
        """
        Process an inbound webhook lead payload.

        Steps:
        1. Resolve the LeadSource by source_key (404 if unknown/inactive).
        2. Verify HMAC-SHA256 signature if the source has a secret configured.
        3. Return the existing IngestionEvent if the idempotency key is duplicate.
        4. Find-or-create a Contact by primary email, then create the Lead.
        5. Commit and return the new IngestionEvent.
        """
        source = await self._load_source(source_key)
        self._verify_signature(source, raw_body, signature)
        tenant_id: uuid.UUID = source.tenant_id

        existing = await self._find_event(tenant_id, source.id, idempotency_key)
        if existing is not None:
            return existing

        event = IngestionEvent(
            tenant_id=tenant_id,
            source_id=source.id,
            idempotency_key=idempotency_key,
            event_type=_SUPPORTED_EVENT_TYPE,
            status="received",
            raw_payload=payload,
        )
        self._session.add(event)
        await self._session.flush()

        contact_data = _extract_contact(payload)
        contact = await self._find_or_create_contact(
            tenant_id=tenant_id,
            email=contact_data.get("email"),
            phone=contact_data.get("phone"),
            first_name=contact_data.get("first_name"),
            last_name=contact_data.get("last_name"),
        )

        lead = Lead(
            tenant_id=tenant_id,
            contact_id=contact.id,
            source_id=source.id,
            ingestion_event_id=event.id,
            status="new",
            lead_type=str(payload.get("lead_type", "unknown")),
            raw_payload=payload,
        )
        self._session.add(lead)
        await self._session.flush()

        event.lead_id = lead.id
        await self._session.flush()

        TimelineService(self._session, tenant_id).log(
            lead.id,
            "lead.created",
            {"source_id": str(source.id), "lead_type": lead.lead_type},
        )
        await self._session.flush()
        await self._session.commit()
        return event

    # ── private helpers ───────────────────────────────────────────────────────

    async def _load_source(self, source_key: str) -> LeadSource:
        result = await self._session.execute(
            sa.select(LeadSource).where(
                LeadSource.source_key == source_key,
                LeadSource.is_active.is_(True),
            )
        )
        source = result.scalar_one_or_none()
        if source is None:
            raise AppError(
                code="source_not_found",
                message=f"Webhook source '{source_key}' not found or inactive",
                status_code=404,
            )
        return source

    @staticmethod
    def _verify_signature(source: LeadSource, body: bytes, signature: str | None) -> None:
        if not source.secret_hash:
            return
        if not signature:
            raise AppError(
                code="missing_signature",
                message="X-Hub-Signature-256 header required for this source",
                status_code=401,
            )
        expected = (
            "sha256="
            + hmac.new(
                source.secret_hash.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
        )
        if not hmac.compare_digest(signature, expected):
            raise AppError(
                code="invalid_signature",
                message="Webhook signature verification failed",
                status_code=401,
            )

    async def _find_event(
        self,
        tenant_id: uuid.UUID,
        source_id: uuid.UUID,
        idempotency_key: str,
    ) -> IngestionEvent | None:
        result = await self._session.execute(
            sa.select(IngestionEvent).where(
                IngestionEvent.tenant_id == tenant_id,
                IngestionEvent.source_id == source_id,
                IngestionEvent.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def _find_or_create_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        email: str | None,
        phone: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> Contact:
        # Dedup by primary email
        if email:
            result = await self._session.execute(
                sa.select(Contact)
                .join(ContactPoint, Contact.id == ContactPoint.contact_id)
                .where(
                    Contact.tenant_id == tenant_id,
                    ContactPoint.type == "email",
                    ContactPoint.value_normalized == email.lower(),
                )
                .limit(1)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing

        contact = Contact(
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
        )
        self._session.add(contact)
        await self._session.flush()

        if email:
            self._session.add(
                ContactPoint(
                    contact_id=contact.id,
                    tenant_id=tenant_id,
                    type="email",
                    value_raw=email,
                    value_normalized=email.lower(),
                    is_primary=True,
                )
            )
        if phone:
            self._session.add(
                ContactPoint(
                    contact_id=contact.id,
                    tenant_id=tenant_id,
                    type="phone",
                    value_raw=phone,
                    is_primary=True,
                )
            )
        if email or phone:
            await self._session.flush()

        return contact


def _extract_contact(payload: dict[str, Any]) -> dict[str, str | None]:
    """Extract contact fields from a generic webhook payload.

    Handles common field name conventions from HubSpot, web forms, etc.
    """
    nested: dict[str, Any] = payload.get("contact", {}) or {}

    def _get(*keys: str) -> str | None:
        for k in keys:
            v = payload.get(k) or nested.get(k)
            if v:
                return str(v).strip()
        return None

    first = _get("first_name", "firstName", "fname")
    last = _get("last_name", "lastName", "lname")

    # Fall back to splitting a full name field
    if not first and not last:
        full = _get("name", "full_name", "fullName")
        if full:
            parts = full.split(" ", 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else None

    return {
        "first_name": first,
        "last_name": last,
        "email": _get("email", "email_address"),
        "phone": _get("phone", "phone_number", "mobile"),
    }
