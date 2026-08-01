"""Add gap_reason to cycle history logs

Revision ID: cycle_gap_reason_005
Revises: user_management_004
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa


revision = "cycle_gap_reason_005"
down_revision = "user_management_004"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    if not _column_exists("cycle_history_logs", "gap_reason"):
        op.add_column(
            "cycle_history_logs",
            sa.Column("gap_reason", sa.String(length=50), nullable=True),
        )


def downgrade():
    if _column_exists("cycle_history_logs", "gap_reason"):
        op.drop_column("cycle_history_logs", "gap_reason")
