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


def upgrade():
    op.add_column(
        "cycle_history_logs",
        sa.Column("gap_reason", sa.String(length=50), nullable=True),
    )


def downgrade():
    op.drop_column("cycle_history_logs", "gap_reason")
