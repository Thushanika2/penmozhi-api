"""Add consent-based one-time cycle sharing.

Revision ID: secure_cycle_sharing_010
Revises: reminder_push_delivery_009
"""

from alembic import op
import sqlalchemy as sa

revision = "secure_cycle_sharing_010"
down_revision = "reminder_push_delivery_009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sharing_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("sharer_user_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("used_by_user_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_sharing_invites_code", "sharing_invites", ["code"], unique=True)
    op.create_index("ix_sharing_invites_sharer_user_id", "sharing_invites", ["sharer_user_id"])
    op.create_table(
        "shared_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sharer_user_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("viewer_user_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("active_sharer_user_id", sa.Integer(), nullable=True),
        sa.Column("active_viewer_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("connected_at", sa.DateTime(), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('active', 'disconnected')", name="ck_shared_connections_status"),
    )
    op.create_index("ix_shared_connections_sharer_user_id", "shared_connections", ["sharer_user_id"])
    op.create_index("ix_shared_connections_viewer_user_id", "shared_connections", ["viewer_user_id"])
    op.create_index("ix_shared_connections_status", "shared_connections", ["status"])
    op.create_index("uq_active_sharer", "shared_connections", ["active_sharer_user_id"], unique=True)
    op.create_index("uq_active_viewer", "shared_connections", ["active_viewer_user_id"], unique=True)


def downgrade():
    op.drop_table("shared_connections")
    op.drop_table("sharing_invites")
