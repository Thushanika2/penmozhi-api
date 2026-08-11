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
from app.routes.tracking_category_routes import tracking_category_bp
from app.routes.custom_tag_routes import custom_tag_bp
from app.routes.pregnancy_profile_routes import pregnancy_profile_bp
from app.routes.perimenopause_log_routes import perimenopause_log_bp
from app.routes.push_subscription_routes import push_api_bp, push_subscription_bp
from app.routes.cycle_share_routes import cycle_share_bp
from app.routes.invitation_routes import invitation_bp
from app.routes.wearable_routes import wearable_bp
from app.routes.subscription_routes import subscription_bp
from app.routes.account_routes import account_bp


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
    app.register_blueprint(tracking_category_bp)
    app.register_blueprint(custom_tag_bp)
    app.register_blueprint(pregnancy_profile_bp)
    app.register_blueprint(perimenopause_log_bp)
    app.register_blueprint(push_subscription_bp)
    app.register_blueprint(push_api_bp)
    app.register_blueprint(cycle_share_bp)
    app.register_blueprint(invitation_bp)
    app.register_blueprint(wearable_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(account_bp)
