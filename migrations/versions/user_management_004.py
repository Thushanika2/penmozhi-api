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


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {
        idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def upgrade():
    if not _column_exists("user_profiles", "status"):
        op.add_column(
            "user_profiles",
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        )
    if not _column_exists("user_profiles", "token_valid_after"):
        op.add_column(
            "user_profiles",
            sa.Column("token_valid_after", sa.DateTime(), nullable=True),
        )
    if not _column_exists("user_profiles", "is_test_account"):
        op.add_column(
            "user_profiles",
            sa.Column(
                "is_test_account",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if not _column_exists("user_profiles", "last_active_at"):
        op.add_column(
            "user_profiles",
            sa.Column("last_active_at", sa.DateTime(), nullable=True),
        )
    if not _column_exists("user_profiles", "login_count"):
        op.add_column(
            "user_profiles",
            sa.Column("login_count", sa.Integer(), nullable=False, server_default="0"),
        )

    if not _table_exists("admin_action_logs"):
        op.create_table(
            "admin_action_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("admin_id", sa.Integer(), nullable=False),
            sa.Column("action_type", sa.String(50), nullable=False),
            sa.Column("target_user_id", sa.Integer(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.ForeignKeyConstraint(["admin_id"], ["user_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["target_user_id"], ["user_profiles.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("admin_action_logs") and not _index_exists(
        "admin_action_logs", "ix_admin_action_logs_target_user_id"
    ):
        op.create_index(
            "ix_admin_action_logs_target_user_id",
            "admin_action_logs",
            ["target_user_id"],
        )
    if _table_exists("admin_action_logs") and not _index_exists(
        "admin_action_logs", "ix_admin_action_logs_admin_id"
    ):
        op.create_index(
            "ix_admin_action_logs_admin_id",
            "admin_action_logs",
            ["admin_id"],
        )


def downgrade():
    if _index_exists("admin_action_logs", "ix_admin_action_logs_admin_id"):
        op.drop_index("ix_admin_action_logs_admin_id", table_name="admin_action_logs")
    if _index_exists("admin_action_logs", "ix_admin_action_logs_target_user_id"):
        op.drop_index(
            "ix_admin_action_logs_target_user_id", table_name="admin_action_logs"
        )
    if _table_exists("admin_action_logs"):
        op.drop_table("admin_action_logs")
    for column in (
        "login_count",
        "last_active_at",
        "is_test_account",
        "token_valid_after",
        "status",
    ):
        if _column_exists("user_profiles", column):
            op.drop_column("user_profiles", column)
