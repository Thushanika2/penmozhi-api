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


def upgrade():
    op.add_column(
        "medication_supplement_reminders",
        sa.Column("adherence_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "medication_supplement_reminders",
        sa.Column("last_push_sent_on", sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column("medication_supplement_reminders", "last_push_sent_on")
    op.drop_column("medication_supplement_reminders", "adherence_date")
