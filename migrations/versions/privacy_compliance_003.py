"""Privacy & compliance tables

Revision ID: privacy_compliance_003
Revises: education_language_002
Create Date: 2026-07-28

"""
from alembic import op
import sqlalchemy as sa


revision = "privacy_compliance_003"
down_revision = "education_language_002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_email", sa.String(120), nullable=False),
        sa.Column("request_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_by_admin_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["completed_by_admin_id"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_privacy_requests_user_id", "privacy_requests", ["user_id"])

    op.create_table(
        "user_consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("policy_version", sa.String(20), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("context", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])


def downgrade():
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")
    op.drop_index("ix_privacy_requests_user_id", table_name="privacy_requests")
    op.drop_table("privacy_requests")
