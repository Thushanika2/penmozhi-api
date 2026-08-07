"""Create education_videos table for standalone education videos

Revision ID: education_videos_008
Revises: education_video_007
Create Date: 2026-08-07

"""
from alembic import op
import sqlalchemy as sa


revision = "education_videos_008"
down_revision = "education_video_007"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade():
    if _table_exists("education_videos"):
        return

    op.create_table(
        "education_videos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(length=512), nullable=False),
        sa.Column("video_public_id", sa.String(length=255), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=512), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    if _table_exists("education_videos"):
        op.drop_table("education_videos")
