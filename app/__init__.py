from flask import Flask, jsonify, request
from sqlalchemy.exc import OperationalError, ProgrammingError
from werkzeug.exceptions import RequestEntityTooLarge

from app.config import Config
from app.extensions import db, jwt, limiter, migrate
from app.routes import register_blueprints


def create_app():
    Config.validate()

    app = Flask(__name__)
    app.config.from_object(Config)
    if Config.JWT_SECRET_KEY_IS_EPHEMERAL:
        app.logger.warning(
            "JWT_SECRET_KEY is not configured; using a secure ephemeral key. "
            "Set a permanent 32+ character JWT_SECRET_KEY so sessions survive restarts."
        )
    elif Config.JWT_SECRET_KEY_WAS_DERIVED:
        app.logger.warning(
            "JWT_SECRET_KEY is shorter than the recommended 32 characters; "
            "using a stable SHA-256-derived signing key. Rotate it to a unique "
            "32+ character value in Railway."
        )
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
        EducationVideo,
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

    @app.after_request
    def prevent_private_response_caching(response):
        """Never allow API or admin responses to enter a shared cache."""
        if request.path.startswith(("/api", "/admin")):
            response.headers["Cache-Control"] = (
                "private, no-store, no-cache, max-age=0, must-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.vary.add("Authorization")
        return response

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
            }), 500
        return jsonify({
            "error": "Database connection failed.",
            "error_code": "db.connection_failed",
        }), 500

    @app.errorhandler(ProgrammingError)
    def handle_programming_error(err):
        db.session.rollback()
        return jsonify({
            "error": "Database schema error. Redeploy the API so migrations can run.",
            "error_code": "db.schema_error",
        }), 500

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_err):
        return jsonify({
            "error": "The video exceeds the 200 MB upload limit.",
            "error_code": "validation.video_too_large",
        }), 413

    @app.errorhandler(500)
    def handle_internal_error(err):
        return jsonify({"error": "An internal server error occurred."}), 500

    return app
