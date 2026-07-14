from flask import Flask, jsonify
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.config import Config
from app.extensions import db, jwt
from app.routes import register_blueprints


def create_app():
    Config.validate()

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    jwt.init_app(app)

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
    )

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return db.session.get(UserProfile, int(identity))

    register_blueprints(app)

    @app.route("/", methods=["GET"])
    def api_home():
        return jsonify({
            "message": "Penmozhi Women's Health API",
            "version": "1.0",
            "endpoints": {
                "auth": "/api/auth",
                "health_profiles": "/api/health-profiles",
                "cycles": "/api/cycles",
                "symptoms": "/api/symptoms",
                "reminders": "/api/reminders",
                "ai_assistant": "/api/ai-assistant",
                "pcos_status": "/api/pcos-status",
                "education": "/api/education",
                "forum": "/api/forum",
            },
        })

    @app.errorhandler(OperationalError)
    def handle_operational_error(err):
        db.session.rollback()
        orig = getattr(err, "orig", None)
        code = orig.args[0] if orig and orig.args else None
        if code == 1049:
            return jsonify({"error": "Invalid database name configured."}), 500
        if code in (2003, 2002):
            return jsonify({"error": "MySQL server is not running or not reachable."}), 503
        return jsonify({"error": "Database connection failed."}), 500

    @app.errorhandler(ProgrammingError)
    def handle_programming_error(err):
        db.session.rollback()
        return jsonify({"error": "Invalid database name configured."}), 500

    @app.errorhandler(500)
    def handle_internal_error(err):
        return jsonify({"error": "An internal server error occurred."}), 500

    return app
