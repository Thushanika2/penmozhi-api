import logging
import os
from datetime import date

from flask import current_app, jsonify
from flask_jwt_extended import current_user
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Config
from app.extensions import db
from app.models import (
    AIHealthAssistantSession,
    CycleHistoryLog,
    EducationalResource,
    ForumComment,
    ForumPost,
    HealthProfile,
    MedicationSupplementReminder,
    PCOSDisorderStatus,
    SymptomTrackingLog,
    UserProfile,
)

logger = logging.getLogger(__name__)

DELETE_ORDER = (
    ForumComment,
    ForumPost,
    SymptomTrackingLog,
    AIHealthAssistantSession,
    MedicationSupplementReminder,
    CycleHistoryLog,
    PCOSDisorderStatus,
    HealthProfile,
    EducationalResource,
    UserProfile,
)

APPLICATION_MODELS = DELETE_ORDER


def _admin_log(action, details=None, admin_id=None, admin_email=None):
    if admin_id is None or admin_email is None:
        try:
            admin_id = admin_id if admin_id is not None else getattr(current_user, "id", None)
            admin_email = (
                admin_email if admin_email is not None else getattr(current_user, "email", None)
            )
        except Exception:
            admin_id = admin_id if admin_id is not None else None
            admin_email = admin_email if admin_email is not None else None

    message = f"Admin action: {action} | admin_id={admin_id} admin_email={admin_email}"
    if details:
        message = f"{message} | {details}"
    logger.info(message)


def _get_admin_context():
    return getattr(current_user, "id", None), getattr(current_user, "email", None)


def _is_development_mode():
    flask_env = os.getenv("FLASK_ENV", "").strip().lower()
    flask_debug = os.getenv("FLASK_DEBUG", "").strip().lower() in ("true", "1", "yes")
    app_debug = bool(current_app.config.get("DEBUG"))
    return flask_env == "development" or flask_debug or app_debug


def _development_only_response(action):
    return jsonify({
        "success": False,
        "error": (
            f"{action} is disabled in this environment. "
            "Set FLASK_ENV=development or FLASK_DEBUG=True to enable."
        ),
    }), 403


def _error_response(action, exc, status=500):
    db.session.rollback()
    logger.exception("Admin %s failed", action)
    return jsonify({
        "success": False,
        "error": f"Failed to {action.replace('-', ' ')}.",
        "details": str(exc),
    }), status


def clear_data():
    """Delete all rows. Table structure and AUTO_INCREMENT counters are preserved."""
    admin_id, admin_email = _get_admin_context()
    _admin_log("clear-data", "starting", admin_id=admin_id, admin_email=admin_email)

    deleted_counts = {}
    try:
        for model in DELETE_ORDER:
            table_name = model.__tablename__
            deleted_counts[table_name] = db.session.query(model).delete(synchronize_session=False)

        db.session.commit()
        _admin_log(
            "clear-data",
            f"success deleted={deleted_counts}",
            admin_id=admin_id,
            admin_email=admin_email,
        )

        return jsonify({
            "success": True,
            "operation": "clear-data",
            "message": "All application data deleted. AUTO_INCREMENT values were not reset.",
            "ids_reset": False,
            "deleted_counts": deleted_counts,
        }), 200
    except SQLAlchemyError as exc:
        return _error_response("clear-data", exc)
    except Exception as exc:
        return _error_response("clear-data", exc)


def truncate_data():
    """Truncate all application tables and reset AUTO_INCREMENT to 1."""
    admin_id, admin_email = _get_admin_context()
    _admin_log("truncate-data", "starting", admin_id=admin_id, admin_email=admin_email)

    truncated_tables = []
    try:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for model in DELETE_ORDER:
            table_name = model.__tablename__
            db.session.execute(text(f"TRUNCATE TABLE `{table_name}`"))
            truncated_tables.append(table_name)
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()

        _admin_log(
            "truncate-data",
            f"success tables={truncated_tables}",
            admin_id=admin_id,
            admin_email=admin_email,
        )

        return jsonify({
            "success": True,
            "operation": "truncate-data",
            "message": "All application tables truncated. New records will start from id=1.",
            "ids_reset": True,
            "truncated_tables": truncated_tables,
        }), 200
    except SQLAlchemyError as exc:
        return _error_response("truncate-data", exc)
    except Exception as exc:
        return _error_response("truncate-data", exc)


def reset_data():
    """Backward-compatible alias for clear_data."""
    return clear_data()


def reset_db():
    """Drop and recreate all tables. Development only."""
    admin_id, admin_email = _get_admin_context()

    if not _is_development_mode():
        _admin_log(
            "reset-db",
            "blocked (not development mode)",
            admin_id=admin_id,
            admin_email=admin_email,
        )
        return _development_only_response("Reset database")

    _admin_log("reset-db", "starting", admin_id=admin_id, admin_email=admin_email)

    try:
        db.drop_all()
        db.create_all()
        db.session.commit()
        _admin_log("reset-db", "success", admin_id=admin_id, admin_email=admin_email)

        return jsonify({
            "success": True,
            "operation": "reset-db",
            "message": "Database dropped and recreated successfully.",
            "ids_reset": True,
            "tables_recreated": [model.__tablename__ for model in APPLICATION_MODELS],
        }), 200
    except SQLAlchemyError as exc:
        return _error_response("reset-db", exc)
    except Exception as exc:
        return _error_response("reset-db", exc)


def _get_migration_info():
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    migrate_ext = current_app.extensions["migrate"]
    config = migrate_ext.migrate.get_config()
    script = ScriptDirectory.from_config(config)

    with db.engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    head_revision = script.get_current_head()
    pending_revisions = []
    if current_revision != head_revision:
        for revision in script.iterate_revisions(head_revision, current_revision):
            if revision.revision != current_revision:
                pending_revisions.append(revision.revision)

    return {
        "current_revision": current_revision,
        "head_revision": head_revision,
        "pending_upgrade": current_revision != head_revision,
        "pending_revisions": pending_revisions,
    }


def migration_status():
    _admin_log("migration-status", "checking")

    try:
        db.session.execute(text("SELECT 1"))
        migration_info = _get_migration_info()

        return jsonify({
            "success": True,
            "operation": "migration-status",
            **migration_info,
        }), 200
    except SQLAlchemyError as exc:
        return _error_response("migration-status", exc)
    except Exception as exc:
        return _error_response("migration-status", exc)


def migration_upgrade():
    admin_id, admin_email = _get_admin_context()
    _admin_log("migration-upgrade", "starting", admin_id=admin_id, admin_email=admin_email)

    try:
        from flask_migrate import upgrade

        upgrade()
        migration_info = _get_migration_info()
        _admin_log("migration-upgrade", "success", admin_id=admin_id, admin_email=admin_email)

        return jsonify({
            "success": True,
            "operation": "migration-upgrade",
            "message": "Database migrations applied successfully.",
            **migration_info,
        }), 200
    except SQLAlchemyError as exc:
        return _error_response("migration-upgrade", exc)
    except Exception as exc:
        return _error_response("migration-upgrade", exc)


def migration_downgrade():
    admin_id, admin_email = _get_admin_context()

    if not _is_development_mode():
        _admin_log(
            "migration-downgrade",
            "blocked (not development mode)",
            admin_id=admin_id,
            admin_email=admin_email,
        )
        return _development_only_response("Migration downgrade")

    _admin_log("migration-downgrade", "starting", admin_id=admin_id, admin_email=admin_email)

    try:
        from flask_migrate import downgrade

        downgrade()
        migration_info = _get_migration_info()
        _admin_log("migration-downgrade", "success", admin_id=admin_id, admin_email=admin_email)

        return jsonify({
            "success": True,
            "operation": "migration-downgrade",
            "message": "Last migration rolled back successfully.",
            **migration_info,
        }), 200
    except SQLAlchemyError as exc:
        return _error_response("migration-downgrade", exc)
    except Exception as exc:
        return _error_response("migration-downgrade", exc)


def seed_admin():
    admin_name = Config.ADMIN_NAME
    admin_email = Config.ADMIN_EMAIL
    admin_password = Config.ADMIN_PASSWORD

    missing = []
    if not admin_name:
        missing.append("ADMIN_NAME")
    if not admin_email:
        missing.append("ADMIN_EMAIL")
    if not admin_password:
        missing.append("ADMIN_PASSWORD")

    if missing:
        return jsonify({
            "success": False,
            "error": "Missing required environment variables.",
            "missing": missing,
        }), 400

    existing = UserProfile.query.filter_by(email=admin_email.strip()).first()
    if existing:
        _admin_log("seed-admin", f"skipped existing admin email={admin_email}")
        return jsonify({
            "success": True,
            "message": "Admin account already exists.",
            "created": False,
            "admin": existing.to_dict(),
        }), 200

    _admin_log("seed-admin", f"creating admin email={admin_email}")

    try:
        admin = UserProfile(
            full_name=admin_name.strip(),
            date_of_birth=date(1990, 1, 1),
            email=admin_email.strip(),
            language_preference="english",
            role="admin",
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

        _admin_log("seed-admin", f"success admin_id={admin.id}")

        return jsonify({
            "success": True,
            "message": "Admin account created successfully.",
            "created": True,
            "admin": admin.to_dict(),
        }), 201
    except SQLAlchemyError as exc:
        return _error_response("seed-admin", exc)
    except Exception as exc:
        return _error_response("seed-admin", exc)


def db_status():
    _admin_log("db-status", "checking")

    try:
        db.session.execute(text("SELECT 1"))
        health_status = "healthy"
    except SQLAlchemyError as exc:
        logger.exception("Database health check failed")
        return jsonify({
            "success": False,
            "health_status": "unhealthy",
            "error": "Database connection check failed.",
            "details": str(exc),
        }), 503

    table_counts = {}
    total_records = 0

    try:
        for model in APPLICATION_MODELS:
            table_name = model.__tablename__
            count = db.session.query(model).count()
            table_counts[table_name] = count
            total_records += count

        inspector = inspect(db.engine)
        db_tables = set(inspector.get_table_names())
        app_tables = {model.__tablename__ for model in APPLICATION_MODELS}
        extra_tables = sorted(db_tables - app_tables)

        for table_name in extra_tables:
            result = db.session.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
            count = result.scalar() or 0
            table_counts[table_name] = count
            total_records += count

        migration_info = _get_migration_info()

        return jsonify({
            "success": True,
            "health_status": health_status,
            "total_tables": len(table_counts),
            "application_tables": len(app_tables),
            "total_records": total_records,
            "table_counts": table_counts,
            **migration_info,
        }), 200
    except SQLAlchemyError as exc:
        return _error_response("db-status", exc)
    except Exception as exc:
        return _error_response("db-status", exc)
