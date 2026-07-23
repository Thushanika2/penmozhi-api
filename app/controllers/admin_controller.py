import csv
import io
import logging
import os
from datetime import date, datetime, timedelta

from flask import current_app, jsonify, make_response, request
from flask_jwt_extended import current_user
from sqlalchemy import inspect, or_, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Config
from app.extensions import db
from app.models import (
    AIHealthAssistantSession,
    CycleHistoryLog,
    DailyLog,
    EducationalResource,
    ForumComment,
    ForumPost,
    HealthProfile,
    MedicationSupplementReminder,
    PCOSDisorderStatus,
    SymptomTrackingLog,
    UserProfile,
)
from app.services.admin_analytics_service import get_platform_analytics

logger = logging.getLogger(__name__)

DELETE_ORDER = (
    ForumComment,
    ForumPost,
    SymptomTrackingLog,
    AIHealthAssistantSession,
    MedicationSupplementReminder,
    DailyLog,
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


def get_analytics():
    days = request.args.get("days", default=30, type=int)
    _admin_log("analytics", f"days={days}")
    return jsonify(get_platform_analytics(days=days)), 200


def list_users():
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(max(1, request.args.get("per_page", default=20, type=int)), 100)
    search = (request.args.get("search") or "").strip()

    query = UserProfile.query.filter(UserProfile.role == "user")
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(UserProfile.email.ilike(like), UserProfile.full_name.ilike(like))
        )

    pagination = query.order_by(UserProfile.registration_date.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return jsonify(
        {
            "users": [user.to_dict() for user in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }
    ), 200


def _csv_response(filename, rows, headers):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def export_report(report_type):
    report_type = (report_type or "").strip().lower()
    _admin_log("export-report", report_type)

    if report_type == "users":
        rows = []
        for user in UserProfile.query.filter_by(role="user").order_by(UserProfile.id.asc()).all():
            rows.append(
                [
                    user.id,
                    user.full_name,
                    user.email,
                    user.language_preference,
                    user.country or "",
                    user.timezone,
                    user.onboarding_completed,
                    user.registration_date.isoformat() if user.registration_date else "",
                ]
            )
        return _csv_response(
            "penmozhi-users.csv",
            rows,
            [
                "id",
                "full_name",
                "email",
                "language_preference",
                "country",
                "timezone",
                "onboarding_completed",
                "registration_date",
            ],
        )

    if report_type == "cycles":
        rows = []
        logs = (
            db.session.query(CycleHistoryLog, UserProfile.email)
            .join(UserProfile, CycleHistoryLog.profile_id == UserProfile.id)
            .order_by(CycleHistoryLog.cycle_start_date.desc())
            .all()
        )
        for log, email in logs:
            rows.append(
                [
                    log.profile_id,
                    email,
                    log.cycle_start_date.isoformat() if log.cycle_start_date else "",
                    log.cycle_end_date.isoformat() if log.cycle_end_date else "",
                    log.flow_intensity,
                    (log.notes or "").replace("\n", " "),
                ]
            )
        return _csv_response(
            "penmozhi-cycles.csv",
            rows,
            ["profile_id", "email", "cycle_start_date", "cycle_end_date", "flow_intensity", "notes"],
        )

    if report_type == "symptoms":
        rows = []
        logs = (
            db.session.query(SymptomTrackingLog, UserProfile.email)
            .join(UserProfile, SymptomTrackingLog.profile_id == UserProfile.id)
            .order_by(SymptomTrackingLog.date_time.desc())
            .all()
        )
        for log, email in logs:
            rows.append(
                [
                    log.profile_id,
                    email,
                    log.date_time.isoformat() if log.date_time else "",
                    log.category,
                    log.pain_severity,
                    log.mood_status or "",
                    log.sleep_metrics or "",
                ]
            )
        return _csv_response(
            "penmozhi-symptoms.csv",
            rows,
            ["profile_id", "email", "date_time", "category", "pain_severity", "mood_status", "sleep_metrics"],
        )

    if report_type == "daily_logs":
        rows = []
        logs = (
            db.session.query(DailyLog, UserProfile.email)
            .join(UserProfile, DailyLog.profile_id == UserProfile.id)
            .order_by(DailyLog.log_date.desc())
            .all()
        )
        for log, email in logs:
            rows.append(
                [
                    log.profile_id,
                    email,
                    log.log_date.isoformat() if log.log_date else "",
                    log.flow_level or "",
                    log.pain_level or "",
                    log.mood or "",
                    log.energy or "",
                    log.sleep_hours if log.sleep_hours is not None else "",
                    log.exercise or "",
                ]
            )
        return _csv_response(
            "penmozhi-daily-logs.csv",
            rows,
            [
                "profile_id",
                "email",
                "log_date",
                "flow_level",
                "pain_level",
                "mood",
                "energy",
                "sleep_hours",
                "exercise",
            ],
        )

    if report_type == "summary":
        analytics = get_platform_analytics(days=30)
        summary = analytics["summary"]
        rows = [[key, value] for key, value in summary.items()]
        rows.append(["generated_at", datetime.utcnow().isoformat()])
        return _csv_response("penmozhi-summary.csv", rows, ["metric", "value"])

    return jsonify({"success": False, "error": "Invalid export type."}), 400
