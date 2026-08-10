"""Extended features migration

Revision ID: ext_features_001
Revises: 
Create Date: 2026-07-26

"""
from alembic import op
import sqlalchemy as sa


revision = "ext_features_001"
down_revision = None
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name):
    return table_name in _inspector().get_table_names()


def _column_exists(table_name, column_name):
    if not _table_exists(table_name):
        return False
    return column_name in {column["name"] for column in _inspector().get_columns(table_name)}


def _foreign_key_exists(table_name, constraint_name, columns, referred_table):
    if not _table_exists(table_name):
        return False
    return any(
        foreign_key.get("name") == constraint_name
        or (
            foreign_key.get("constrained_columns") == columns
            and foreign_key.get("referred_table") == referred_table
        )
        for foreign_key in _inspector().get_foreign_keys(table_name)
    )


def upgrade():
    if not _column_exists("user_profiles", "mode"):
        op.add_column("user_profiles", sa.Column("mode", sa.String(30), nullable=False, server_default="period"))
    if not _column_exists("user_profiles", "pin_hash"):
        op.add_column("user_profiles", sa.Column("pin_hash", sa.String(255), nullable=True))

    if not _table_exists("tracking_categories"):
        op.create_table(
        "tracking_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("label_ta", sa.String(255), nullable=False),
        sa.Column("group", sa.String(50), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        )

    if not _table_exists("custom_tags"):
        op.create_table(
        "custom_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "label", name="uq_custom_tag_profile_label"),
        )

    if not _column_exists("symptom_tracking_logs", "tracking_category_id"):
        op.add_column("symptom_tracking_logs", sa.Column("tracking_category_id", sa.Integer(), nullable=True))
    if not _column_exists("symptom_tracking_logs", "custom_tag_id"):
        op.add_column("symptom_tracking_logs", sa.Column("custom_tag_id", sa.Integer(), nullable=True))
    if not _foreign_key_exists("symptom_tracking_logs", "fk_symptom_tracking_category", ["tracking_category_id"], "tracking_categories"):
        op.create_foreign_key("fk_symptom_tracking_category", "symptom_tracking_logs", "tracking_categories", ["tracking_category_id"], ["id"])
    if not _foreign_key_exists("symptom_tracking_logs", "fk_symptom_custom_tag", ["custom_tag_id"], "custom_tags"):
        op.create_foreign_key("fk_symptom_custom_tag", "symptom_tracking_logs", "custom_tags", ["custom_tag_id"], ["id"])

    if not _column_exists("daily_logs", "sleep_source"):
        op.add_column("daily_logs", sa.Column("sleep_source", sa.String(50), nullable=True))
    if not _column_exists("health_profiles", "last_notified_for"):
        op.add_column("health_profiles", sa.Column("last_notified_for", sa.Date(), nullable=True))

    if not _table_exists("pregnancy_profiles"):
        op.create_table(
        "pregnancy_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("last_menstrual_period", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("current_trimester", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id"),
        )

    if not _table_exists("perimenopause_logs"):
        op.create_table(
        "perimenopause_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("hot_flashes", sa.Boolean(), nullable=False),
        sa.Column("night_sweats", sa.Boolean(), nullable=False),
        sa.Column("mood_changes", sa.String(255), nullable=True),
        sa.Column("sleep_disruption", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "log_date", name="uq_perimenopause_log_profile_date"),
        )

    if not _table_exists("push_subscriptions"):
        op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("cycle_shares"):
        op.create_table(
        "cycle_shares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_profile_id", sa.Integer(), nullable=False),
        sa.Column("shared_with_email", sa.String(120), nullable=False),
        sa.Column("shared_with_profile_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_profile_id"], ["user_profiles.id"]),
        sa.ForeignKeyConstraint(["shared_with_profile_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("wearable_connections"):
        op.create_table(
        "wearable_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "provider", name="uq_wearable_profile_provider"),
        )

    if not _table_exists("subscriptions"):
        op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id"),
        )


def downgrade():
    op.drop_table("subscriptions")
    op.drop_table("wearable_connections")
    op.drop_table("cycle_shares")
    op.drop_table("push_subscriptions")
    op.drop_table("perimenopause_logs")
    op.drop_table("pregnancy_profiles")
    op.drop_column("health_profiles", "last_notified_for")
    op.drop_column("daily_logs", "sleep_source")
    op.drop_constraint("fk_symptom_custom_tag", "symptom_tracking_logs", type_="foreignkey")
    op.drop_constraint("fk_symptom_tracking_category", "symptom_tracking_logs", type_="foreignkey")
    op.drop_column("symptom_tracking_logs", "custom_tag_id")
    op.drop_column("symptom_tracking_logs", "tracking_category_id")
    op.drop_table("custom_tags")
    op.drop_table("tracking_categories")
    op.drop_column("user_profiles", "pin_hash")
    op.drop_column("user_profiles", "mode")
