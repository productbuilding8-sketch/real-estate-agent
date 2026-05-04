"""V2 Lead Ingestion domain: lead_sources, ingestion_events, contacts, contact_points, leads,
lead_preferences, lead_scores, lead_next_actions, dedupe_candidates, contact_merge_events.

Revision ID: a1b2c3d4e5f6
Revises: 9f3c8d2e1a4b
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "9f3c8d2e1a4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_key", sa.String(100), nullable=False),
        sa.Column("secret_hash", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source_key", name="uq_lead_sources_source_key"),
    )
    op.create_index("ix_lead_sources_tenant_id", "lead_sources", ["tenant_id"])

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("is_merged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_contacts_tenant_id", "contacts", ["tenant_id"])

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lead_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ingestion_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="new"),
        sa.Column("lead_type", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("raw_payload", postgresql.JSONB, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("assigned_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_leads_tenant_status", "leads", ["tenant_id", "status"])
    op.create_index("ix_leads_tenant_agent", "leads", ["tenant_id", "assigned_agent_id"])
    op.create_index("ix_leads_tenant_created", "leads", ["tenant_id", "created_at"])
    op.create_index("ix_leads_contact_id", "leads", ["contact_id"])

    # ingestion_events references leads.id — created after leads
    op.create_table(
        "ingestion_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lead_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="received"),
        sa.Column("raw_payload", postgresql.JSONB, nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "source_id", "idempotency_key", name="uq_ingestion_events_idempotency"),
    )
    op.create_index("ix_ingestion_events_source_id", "ingestion_events", ["source_id"])
    op.create_index("ix_ingestion_events_status", "ingestion_events", ["status"])

    # Now add the FK from leads to ingestion_events (was deferred above)
    op.execute(
        "ALTER TABLE leads ADD CONSTRAINT fk_leads_ingestion_event_id "
        "FOREIGN KEY (ingestion_event_id) REFERENCES ingestion_events(id) ON DELETE SET NULL"
    )

    op.create_table(
        "contact_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("value_raw", sa.String(500), nullable=False),
        sa.Column("value_normalized", sa.String(500), nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_contact_points_contact_id", "contact_points", ["contact_id"])
    op.create_index("ix_contact_points_lookup", "contact_points", ["tenant_id", "type", "value_normalized"])

    op.create_table(
        "lead_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("budget_min", sa.Float, nullable=True),
        sa.Column("budget_max", sa.Float, nullable=True),
        sa.Column("location_city", sa.String(255), nullable=True),
        sa.Column("location_state", sa.String(100), nullable=True),
        sa.Column("property_types", postgresql.JSONB, nullable=True),
        sa.Column("timeline", sa.String(50), nullable=True),
        sa.Column("financing_status", sa.String(50), nullable=True),
        sa.Column("purpose", sa.String(50), nullable=True),
        sa.Column("appointment_preferred", sa.Boolean, nullable=True),
        sa.Column("raw_extraction", postgresql.JSONB, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("lead_id", name="uq_lead_preferences_lead_id"),
    )

    op.create_table(
        "lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("scoring_model", sa.String(50), nullable=False, server_default="v1"),
        sa.Column("factors", postgresql.JSONB, nullable=True),
        sa.Column("ai_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("crm_score_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_lead_scores_lead_id", "lead_scores", ["lead_id"])

    op.create_table(
        "lead_next_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("crm_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_lead_next_actions_lead_id", "lead_next_actions", ["lead_id"])

    op.create_table(
        "dedupe_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_a_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_b_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_score", sa.Float, nullable=False),
        sa.Column("match_signals", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("contact_a_id", "contact_b_id", name="uq_dedupe_candidates_pair"),
    )
    op.create_index("ix_dedupe_candidates_tenant_id", "dedupe_candidates", ["tenant_id"])

    op.create_table(
        "contact_merge_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("winner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("loser_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("merged_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("merge_reason", sa.String(100), nullable=True),
        sa.Column("field_decisions", postgresql.JSONB, nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_contact_merge_events_tenant_id", "contact_merge_events", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("contact_merge_events")
    op.drop_table("dedupe_candidates")
    op.drop_table("lead_next_actions")
    op.drop_table("lead_scores")
    op.drop_table("lead_preferences")
    op.drop_table("contact_points")
    op.execute("ALTER TABLE leads DROP CONSTRAINT IF EXISTS fk_leads_ingestion_event_id")
    op.drop_table("ingestion_events")
    op.drop_table("leads")
    op.drop_table("contacts")
    op.drop_table("lead_sources")
