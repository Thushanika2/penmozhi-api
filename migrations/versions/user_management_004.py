"""User management fields and admin action log

Revision ID: user_management_004
Revises: privacy_compliance_003
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa


revision = "user_management_004"
down_revision = "privacy_compliance_003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_profiles",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("token_valid_after", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "is_test_account",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "user_profiles",
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("login_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "admin_action_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["admin_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_action_logs_target_user_id",
        "admin_action_logs",
        ["target_user_id"],
    )
    op.create_index(
        "ix_admin_action_logs_admin_id",
        "admin_action_logs",
        ["admin_id"],
    )


def downgrade():
    op.drop_index("ix_admin_action_logs_admin_id", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_target_user_id", table_name="admin_action_logs")
    op.drop_table("admin_action_logs")
    op.drop_column("user_profiles", "login_count")
    op.drop_column("user_profiles", "last_active_at")
    op.drop_column("user_profiles", "is_test_account")
    op.drop_column("user_profiles", "token_valid_after")
    op.drop_column("user_profiles", "status")
