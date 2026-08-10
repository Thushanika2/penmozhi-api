"""Track daily reminder push delivery and adherence.

Revision ID: reminder_push_delivery_009
Revises: education_videos_008
"""

from alembic import op
import sqlalchemy as sa


revision = "reminder_push_delivery_009"
down_revision = "education_videos_008"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    if not _column_exists("medication_supplement_reminders", "adherence_date"):
        op.add_column(
            "medication_supplement_reminders",
            sa.Column("adherence_date", sa.Date(), nullable=True),
        )
    if not _column_exists("medication_supplement_reminders", "last_push_sent_on"):
        op.add_column(
            "medication_supplement_reminders",
            sa.Column("last_push_sent_on", sa.Date(), nullable=True),
        )


def downgrade():
    if _column_exists("medication_supplement_reminders", "last_push_sent_on"):
        op.drop_column("medication_supplement_reminders", "last_push_sent_on")
    if _column_exists("medication_supplement_reminders", "adherence_date"):
        op.drop_column("medication_supplement_reminders", "adherence_date")
