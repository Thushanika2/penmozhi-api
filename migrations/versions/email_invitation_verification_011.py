"""Bind hashed cycle invitations to email addresses.

Revision ID: email_invitation_verification_011
Revises: secure_cycle_sharing_010
"""

from alembic import op
import sqlalchemy as sa

revision = "email_invitation_verification_011"
down_revision = "secure_cycle_sharing_010"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sharing_invites") as batch:
        batch.add_column(sa.Column("invited_email", sa.String(120), nullable=True))
        batch.add_column(sa.Column("code_hash", sa.String(255), nullable=True))
        batch.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="invalidated"))
        batch.add_column(sa.Column("verification_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch.alter_column("code", existing_type=sa.String(64), nullable=True)
        batch.create_index("ix_sharing_invites_email", ["invited_email"])
        batch.create_index("ix_sharing_invites_status", ["status"])
    # Legacy plaintext invitations are deliberately invalidated and never migrated into hashes.


def downgrade():
    with op.batch_alter_table("sharing_invites") as batch:
        batch.drop_index("ix_sharing_invites_status")
        batch.drop_index("ix_sharing_invites_email")
        batch.drop_column("verification_attempts")
        batch.drop_column("status")
        batch.drop_column("code_hash")
        batch.drop_column("invited_email")
