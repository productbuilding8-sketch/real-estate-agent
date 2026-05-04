"""SLA/Consent domain ORM models (V2): 5 tables."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from dealflow.db.session import Base


class TenantSlaSettings(Base):
    __tablename__ = "tenant_sla_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    first_response_min: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    agent_followup_hrs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="24")
    stale_lead_hrs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="72")
    escalation_hrs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="48")
    custom_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_sla_settings_tenant_id"),)


class LeadSlaResult(Base):
    __tablename__ = "lead_sla_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    first_response_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_response_mins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_followup_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    stale_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("lead_id", name="uq_lead_sla_results_lead_id"),)


class MessagingPolicySettings(Base):
    __tablename__ = "messaging_policy_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    sms_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.true())
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.true())
    imessage_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    rcs_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    auto_send_sms: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    auto_send_whatsapp: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    auto_send_email: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.false())
    custom_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_messaging_policy_settings_tenant_id"),)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="unknown")
    source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("contact_id", "channel", name="uq_consent_records_contact_channel"),
        Index("ix_consent_records_contact_id", "contact_id"),
    )


class OptOutRecord(Base):
    __tablename__ = "opt_out_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    trigger: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    opted_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reinstated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_opt_out_records_contact_id", "contact_id"),)
