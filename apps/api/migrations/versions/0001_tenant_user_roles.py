"""V2 Tenant/Auth schema: tenants, users, roles, tenant_memberships, agent_profiles, tenant_invitations.

Revision ID: 9f3c8d2e1a4b
Revises:
Create Date: 2026-05-03
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9f3c8d2e1a4b"
down_revision = None
branch_labels = None
depends_on = None

_SYSTEM_ROLES = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Owner Admin",
        "slug": "owner_admin",
        "description": "Full tenant control including billing, settings, and all user management",
        "permissions": json.dumps(["*"]),
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "Manager",
        "slug": "manager",
        "description": "Approve AI actions, reassign leads, view all reports, manage agents",
        "permissions": json.dumps(["leads:*", "approvals:*", "tasks:*", "reports:*", "agents:read"]),
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "name": "Agent",
        "slug": "agent",
        "description": "Handle assigned leads, conversations, tasks, and appointments",
        "permissions": json.dumps(["leads:read", "leads:update", "conversations:*", "tasks:*", "appointments:*"]),
    },
    {
        "id": "00000000-0000-0000-0000-000000000004",
        "name": "Implementation Admin",
        "slug": "implementation_admin",
        "description": "Configure integrations, sources, and tenant settings; access raw payloads for debugging",
        "permissions": json.dumps(["settings:*", "integrations:*", "sources:*", "raw_payloads:read"]),
    },
    {
        "id": "00000000-0000-0000-0000-000000000005",
        "name": "Auditor",
        "slug": "auditor",
        "description": "Read-only access to audit logs, reports, and activity timelines",
        "permissions": json.dumps(["audit_logs:read", "reports:read", "activity_timeline:read"]),
    },
]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False, server_default="UTC"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("settings", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("auth0_sub", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("auth0_sub", name="uq_users_auth0_sub"),
    )

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("permissions", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_roles_name"),
        sa.UniqueConstraint("slug", name="uq_roles_slug"),
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_slug", sa.String(100), nullable=False),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_tenant_memberships_user_tenant"),
    )
    op.create_index("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"])

    op.create_table(
        "agent_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("languages", postgresql.JSONB, nullable=True),
        sa.Column("property_types", postgresql.JSONB, nullable=True),
        sa.Column("service_areas", postgresql.JSONB, nullable=True),
        sa.Column("max_leads", sa.Integer, nullable=False, server_default="20"),
        sa.Column("is_available", sa.Boolean, nullable=False, server_default=sa.true()),
        # default_calendar_connection_id FK added in migration 0005 after integration_connections exists
        sa.Column("default_calendar_connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_agent_profiles_user_tenant"),
    )
    op.create_index("ix_agent_profiles_tenant_id", "agent_profiles", ["tenant_id"])

    op.create_table(
        "tenant_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role_slug", sa.String(100), nullable=False),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token", name="uq_tenant_invitations_token"),
    )
    op.create_index("ix_tenant_invitations_tenant_id", "tenant_invitations", ["tenant_id"])

    # Seed system roles
    for role in _SYSTEM_ROLES:
        op.execute(
            sa.text(
                "INSERT INTO roles (id, name, slug, description, permissions, created_at) "
                "VALUES (CAST(:id AS uuid), :name, :slug, :description, CAST(:permissions AS jsonb), now())"
            ).bindparams(
                id=role["id"],
                name=role["name"],
                slug=role["slug"],
                description=role["description"],
                permissions=role["permissions"],
            )
        )


def downgrade() -> None:
    op.drop_table("tenant_invitations")
    op.drop_table("agent_profiles")
    op.drop_table("tenant_memberships")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("tenants")
