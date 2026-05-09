"""Seed a local dev user and membership for DEV_MODE bypass.

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-05-09
"""

import sqlalchemy as sa
from alembic import op

revision = "g7h8i9j0k1l2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None

DEV_USER_ID = "20000000-0000-0000-0000-000000000001"
DEV_AUTH0_SUB = "dev|local"
DEV_MEMBERSHIP_ID = "20000000-0000-0000-0000-000000000002"
DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            INSERT INTO users (id, auth0_sub, email, name, is_active)
            VALUES (:id, :sub, :email, :name, true)
            ON CONFLICT (auth0_sub) DO NOTHING
            """
        ),
        {
            "id": DEV_USER_ID,
            "sub": DEV_AUTH0_SUB,
            "email": "dev@local.dev",
            "name": "Local Dev",
        },
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO tenant_memberships (id, user_id, tenant_id, role_slug, is_active)
            VALUES (:id, :user_id, :tenant_id, 'owner_admin', true)
            ON CONFLICT (user_id, tenant_id) DO NOTHING
            """
        ),
        {
            "id": DEV_MEMBERSHIP_ID,
            "user_id": DEV_USER_ID,
            "tenant_id": DEMO_TENANT_ID,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM tenant_memberships WHERE id = :id"), {"id": DEV_MEMBERSHIP_ID})
    conn.execute(sa.text("DELETE FROM users WHERE auth0_sub = :sub"), {"sub": DEV_AUTH0_SUB})
