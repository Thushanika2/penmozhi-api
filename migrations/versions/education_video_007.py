"""Add Cloudinary video fields to educational resources

Revision ID: education_video_007
Revises: ai_session_updated_006
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa


revision = "education_video_007"
down_revision = "ai_session_updated_006"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    if not _column_exists("educational_resources", "video_url"):
        op.add_column(
            "educational_resources",
            sa.Column("video_url", sa.String(length=512), nullable=True),
        )
    if not _column_exists("educational_resources", "video_public_id"):
        op.add_column(
            "educational_resources",
            sa.Column("video_public_id", sa.String(length=255), nullable=True),
        )


def downgrade():
    if _column_exists("educational_resources", "video_public_id"):
        op.drop_column("educational_resources", "video_public_id")
    if _column_exists("educational_resources", "video_url"):
        op.drop_column("educational_resources", "video_url")
