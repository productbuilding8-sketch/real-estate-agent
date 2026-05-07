"""Seed demo tenant and webhook lead sources for development/demo.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"

SOURCES = [
    {
        "id": "10000000-0000-0000-0000-000000000001",
        "tenant_id": DEMO_TENANT_ID,
        "type": "webhook",
        "name": "Zillow Webhook",
        "source_key": "zillow-demo",
        "secret_hash": None,
        "is_active": True,
        "config": '{"provider": "zillow", "event_types": ["new_inquiry"]}',
    },
    {
        "id": "10000000-0000-0000-0000-000000000002",
        "tenant_id": DEMO_TENANT_ID,
        "type": "crm",
        "name": "HubSpot CRM",
        "source_key": "hubspot-demo",
        "secret_hash": None,
        "is_active": True,
        "config": '{"provider": "hubspot", "sync_direction": "inbound"}',
    },
    {
        "id": "10000000-0000-0000-0000-000000000003",
        "tenant_id": DEMO_TENANT_ID,
        "type": "manual",
        "name": "Web Form",
        "source_key": "web-form-demo",
        "secret_hash": None,
        "is_active": True,
        "config": None,
    },
]


def upgrade() -> None:
    conn = op.get_bind()

    # Upsert demo tenant
    conn.execute(
        sa.text(
            """
            INSERT INTO tenants (id, name, slug, timezone, is_active)
            VALUES (:id, :name, :slug, 'UTC', true)
            ON CONFLICT (slug) DO NOTHING
            """
        ),
        {"id": DEMO_TENANT_ID, "name": "Demo Agency", "slug": "demo"},
    )

    # Upsert each lead source
    for src in SOURCES:
        conn.execute(
            sa.text(
                """
                INSERT INTO lead_sources
                    (id, tenant_id, type, name, source_key, secret_hash, is_active, config)
                VALUES
                    (:id, :tenant_id, :type, :name, :source_key, :secret_hash, :is_active,
                     :config::jsonb)
                ON CONFLICT (source_key) DO NOTHING
                """
            ),
            src,
        )


def downgrade() -> None:
    conn = op.get_bind()

    for src in SOURCES:
        conn.execute(
            sa.text("DELETE FROM lead_sources WHERE source_key = :key"),
            {"key": src["source_key"]},
        )

    conn.execute(
        sa.text("DELETE FROM tenants WHERE slug = 'demo'"),
    )
