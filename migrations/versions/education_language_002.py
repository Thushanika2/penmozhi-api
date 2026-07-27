"""Add language to educational resources

Revision ID: education_language_002
Revises: ext_features_001
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa


revision = "education_language_002"
down_revision = "ext_features_001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "educational_resources",
        sa.Column("language", sa.String(20), nullable=False, server_default="english"),
    )


def downgrade():
    op.drop_column("educational_resources", "language")
