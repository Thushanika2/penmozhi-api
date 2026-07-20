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


def _is_development_mode():
    flask_env = os.getenv("FLASK_ENV", "").strip().lower()
    flask_debug = os.getenv("FLASK_DEBUG", "").strip().lower() in ("true", "1", "yes")
    app_debug = bool(current_app.config.get("DEBUG"))
    return flask_env == "development" or flask_debug or app_debug


def reset_data():
    admin_id = getattr(current_user, "id", None)
    admin_email = getattr(current_user, "email", None)
    _admin_log("reset-data", "starting", admin_id=admin_id, admin_email=admin_email)

    deleted_counts = {}
    try:
        for model in DELETE_ORDER:
            table_name = model.__tablename__
            deleted_counts[table_name] = db.session.query(model).delete(synchronize_session=False)

        db.session.commit()
        _admin_log(
            "reset-data",
            f"success deleted={deleted_counts}",
            admin_id=admin_id,
            admin_email=admin_email,
        )

        return jsonify({
            "success": True,
            "message": "All application data deleted successfully.",
            "deleted_counts": deleted_counts,
        }), 200
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("Admin reset-data failed")
        return jsonify({
            "success": False,
            "error": "Failed to reset application data.",
            "details": str(exc),
        }), 500
    except Exception as exc:
        db.session.rollback()
        logger.exception("Admin reset-data failed")
        return jsonify({
            "success": False,
            "error": "An internal server error occurred.",
            "details": str(exc),
        }), 500


def reset_db():
    admin_id = getattr(current_user, "id", None)
    admin_email = getattr(current_user, "email", None)

    if not _is_development_mode():
        _admin_log(
            "reset-db",
            "blocked (not development mode)",
            admin_id=admin_id,
            admin_email=admin_email,
        )
        return jsonify({
            "success": False,
            "error": (
                "Reset database is disabled in this environment. "
                "Set FLASK_ENV=development or FLASK_DEBUG=True to enable."
            ),
        }), 403

    _admin_log("reset-db", "starting", admin_id=admin_id, admin_email=admin_email)

    try:
        db.drop_all()
        db.create_all()
        db.session.commit()
        _admin_log("reset-db", "success", admin_id=admin_id, admin_email=admin_email)

        return jsonify({
            "success": True,
            "message": "Database dropped and recreated successfully.",
            "tables_recreated": [model.__tablename__ for model in APPLICATION_MODELS],
        }), 200
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("Admin reset-db failed")
        return jsonify({
            "success": False,
            "error": "Failed to reset database.",
            "details": str(exc),
        }), 500
    except Exception as exc:
        db.session.rollback()
        logger.exception("Admin reset-db failed")
        return jsonify({
            "success": False,
            "error": "An internal server error occurred.",
            "details": str(exc),
        }), 500


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
        db.session.rollback()
        logger.exception("Admin seed-admin failed")
        return jsonify({
            "success": False,
            "error": "Failed to create admin account.",
            "details": str(exc),
        }), 500
    except Exception as exc:
        db.session.rollback()
        logger.exception("Admin seed-admin failed")
        return jsonify({
            "success": False,
            "error": "An internal server error occurred.",
            "details": str(exc),
        }), 500


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

        return jsonify({
            "success": True,
            "health_status": health_status,
            "total_tables": len(table_counts),
            "application_tables": len(app_tables),
            "total_records": total_records,
            "table_counts": table_counts,
        }), 200
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("Admin db-status failed")
        return jsonify({
            "success": False,
            "health_status": "degraded",
            "error": "Failed to retrieve database status.",
            "details": str(exc),
        }), 500
    except Exception as exc:
        db.session.rollback()
        logger.exception("Admin db-status failed")
        return jsonify({
            "success": False,
            "health_status": "degraded",
            "error": "An internal server error occurred.",
            "details": str(exc),
        }), 500
