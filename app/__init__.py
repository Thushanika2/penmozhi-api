from flask import Flask, jsonify
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.config import Config
from app.extensions import db, jwt, limiter, migrate
from app.routes import register_blueprints


def create_app():
    Config.validate()

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    from app.services.cloudinary_service import init_cloudinary

    init_cloudinary(app)

    from app.models import (  # noqa: F401
        UserProfile,
        HealthProfile,
        CycleHistoryLog,
        SymptomTrackingLog,
        MedicationSupplementReminder,
        AIHealthAssistantSession,
        PCOSDisorderStatus,
        EducationalResource,
        ForumPost,
        ForumComment,
        DailyLog,
        PasswordResetToken,
        TrackingCategory,
        CustomTag,
        PregnancyProfile,
        PerimenopauseLog,
        PushSubscription,
        CycleShare,
        WearableConnection,
        Subscription,
        PrivacyRequest,
        UserConsent,
        AdminActionLog,
    )

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return db.session.get(UserProfile, int(identity))

    register_blueprints(app)

    from app.services.scheduler_service import init_scheduler

    init_scheduler(app)

    @app.route("/api/health", methods=["GET"])
    def api_health():
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "database": "connected"}), 200
        except Exception as exc:
            return (
                jsonify(
                    {
                        "status": "error",
                        "database": "disconnected",
                        "error": "Database connection failed.",
                        "detail": str(exc.__class__.__name__),
                    }
                ),
                503,
            )

    @app.errorhandler(OperationalError)
    def handle_operational_error(err):
        db.session.rollback()
        orig = getattr(err, "orig", None)
        code = orig.args[0] if orig and orig.args else None
        message = str(orig) if orig else str(err)

        if code == 1049:
            return jsonify({"error": "Invalid database name configured.", "error_code": "db.invalid_name"}), 500
        if code in (2003, 2002):
            return jsonify({
                "error": "MySQL server is not running or not reachable.",
                "error_code": "db.unreachable",
            }), 503
        if code == 1045:
            return jsonify({
                "error": "Database authentication failed. Check Railway MySQL credentials.",
                "error_code": "db.auth_failed",
            }), 500
        if code in (1054, 1146, 1050):
            return jsonify({
                "error": "Database schema is out of date. Redeploy the API so migrations can run.",
                "error_code": "db.schema_mismatch",
                "detail": message,
            }), 500
        return jsonify({
            "error": "Database connection failed.",
            "error_code": "db.connection_failed",
            "detail": message,
        }), 500

    @app.errorhandler(ProgrammingError)
    def handle_programming_error(err):
        db.session.rollback()
        return jsonify({
            "error": "Database schema error. Redeploy the API so migrations can run.",
            "error_code": "db.schema_error",
        }), 500

    @app.errorhandler(500)
    def handle_internal_error(err):
        return jsonify({"error": "An internal server error occurred."}), 500

    return app
