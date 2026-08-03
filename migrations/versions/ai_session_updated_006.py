"""Add updated_at to AI health assistant sessions

Revision ID: ai_session_updated_006
Revises: cycle_gap_reason_005
Create Date: 2026-08-03

"""
from alembic import op
import sqlalchemy as sa


revision = "ai_session_updated_006"
down_revision = "cycle_gap_reason_005"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    if not _column_exists("ai_health_assistant_sessions", "updated_at"):
        op.add_column(
            "ai_health_assistant_sessions",
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        # Backfill from created_at so existing rows sort sensibly.
        op.execute(
            sa.text(
                "UPDATE ai_health_assistant_sessions "
                "SET updated_at = created_at "
                "WHERE updated_at IS NULL"
            )
        )


def downgrade():
    if _column_exists("ai_health_assistant_sessions", "updated_at"):
        op.drop_column("ai_health_assistant_sessions", "updated_at")
