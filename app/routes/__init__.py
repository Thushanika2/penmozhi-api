from app.routes.admin_routes import admin_bp
from app.routes.auth_routes import auth_bp
from app.routes.health_profile_routes import health_profile_bp
from app.routes.cycle_routes import cycle_bp
from app.routes.symptom_routes import symptom_bp
from app.routes.reminder_routes import reminder_bp
from app.routes.ai_assistant_routes import ai_assistant_bp
from app.routes.pcos_status_routes import pcos_status_bp
from app.routes.daily_log_routes import daily_log_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.education_routes import education_bp
from app.routes.forum_routes import forum_bp
from app.routes.onboarding_routes import onboarding_bp
from app.routes.insights_routes import insights_bp


def register_blueprints(app):
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(health_profile_bp)
    app.register_blueprint(cycle_bp)
    app.register_blueprint(symptom_bp)
    app.register_blueprint(reminder_bp)
    app.register_blueprint(ai_assistant_bp)
    app.register_blueprint(pcos_status_bp)
    app.register_blueprint(education_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(daily_log_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(insights_bp)
