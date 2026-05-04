"""V2 Integrations, SLA/Consent, Workflow: integration_connections, crm_mappings, sync_logs,
tenant_sla_settings, lead_sla_results, messaging_policy_settings, consent_records,
opt_out_records, outbox_events. Also adds FK agent_profiles.default_calendar_connection_id.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="disconnected"),
        sa.Column("credentials_enc", sa.Text, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_msg", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_integration_connections_tenant_id", "integration_connections", ["tenant_id"])

    # Add the deferred FK: agent_profiles.default_calendar_connection_id
    op.execute(
        "ALTER TABLE agent_profiles ADD CONSTRAINT fk_agent_profiles_calendar_connection "
        "FOREIGN KEY (default_calendar_connection_id) REFERENCES integration_connections(id) ON DELETE SET NULL"
    )

    op.create_table(
        "crm_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dealflow_field", sa.String(255), nullable=False),
        sa.Column("crm_field", sa.String(255), nullable=False),
        sa.Column("crm_object", sa.String(50), nullable=False),
        sa.Column("idempotency_key_field", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_crm_mappings_connection_id", "crm_mappings", ["connection_id"])

    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="success"),
        sa.Column("crm_record_id", sa.String(255), nullable=True),
        sa.Column("request_ref", postgresql.JSONB, nullable=True),
        sa.Column("response_ref", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("connection_id", "idempotency_key", name="uq_sync_logs_idempotency"),
    )
    op.create_index("ix_sync_logs_connection_id", "sync_logs", ["connection_id"])
    op.create_index("ix_sync_logs_retry", "sync_logs", ["connection_id", "status", "next_retry_at"])

    op.create_table(
        "tenant_sla_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_response_min", sa.Integer, nullable=False, server_default="15"),
        sa.Column("agent_followup_hrs", sa.Integer, nullable=False, server_default="24"),
        sa.Column("stale_lead_hrs", sa.Integer, nullable=False, server_default="72"),
        sa.Column("escalation_hrs", sa.Integer, nullable=False, server_default="48"),
        sa.Column("custom_rules", postgresql.JSONB, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_sla_settings_tenant_id"),
    )

    op.create_table(
        "lead_sla_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_response_met", sa.Boolean, nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_response_mins", sa.Integer, nullable=True),
        sa.Column("agent_followup_met", sa.Boolean, nullable=True),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("stale_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_escalated", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("lead_id", name="uq_lead_sla_results_lead_id"),
    )

    op.create_table(
        "messaging_policy_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sms_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("whatsapp_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("email_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("imessage_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("rcs_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("auto_send_sms", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("auto_send_whatsapp", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("auto_send_email", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("custom_rules", postgresql.JSONB, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_messaging_policy_settings_tenant_id"),
    )

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("source", sa.String(30), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("contact_id", "channel", name="uq_consent_records_contact_channel"),
    )
    op.create_index("ix_consent_records_contact_id", "consent_records", ["contact_id"])

    op.create_table(
        "opt_out_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("trigger", sa.String(50), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reinstated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_opt_out_records_contact_id", "opt_out_records", ["contact_id"])

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("aggregate_type", sa.String(50), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        "CREATE INDEX ix_outbox_events_pending ON outbox_events (status, next_attempt_at) "
        "WHERE status != 'processed'"
    )


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("opt_out_records")
    op.drop_table("consent_records")
    op.drop_table("messaging_policy_settings")
    op.drop_table("lead_sla_results")
    op.drop_table("tenant_sla_settings")
    op.drop_table("sync_logs")
    op.drop_table("crm_mappings")
    op.execute("ALTER TABLE agent_profiles DROP CONSTRAINT IF EXISTS fk_agent_profiles_calendar_connection")
    op.drop_table("integration_connections")
