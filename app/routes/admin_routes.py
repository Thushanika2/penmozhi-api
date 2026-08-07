from flask import Blueprint

from app.controllers import admin_controller as ctrl
from app.controllers import admin_user_controller as user_ctrl
from app.controllers import privacy_admin_controller as privacy_ctrl
from app.middleware import roles_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/clear-data", methods=["POST"])
@roles_required("admin")
def clear_data():
    return ctrl.clear_data()


@admin_bp.route("/truncate-data", methods=["POST"])
@roles_required("admin")
def truncate_data():
    return ctrl.truncate_data()


@admin_bp.route("/reset-data", methods=["POST"])
@roles_required("admin")
def reset_data():
    return ctrl.reset_data()


@admin_bp.route("/reset-db", methods=["POST"])
@roles_required("admin")
def reset_db():
    return ctrl.reset_db()


@admin_bp.route("/migration/status", methods=["GET"])
@roles_required("admin")
def migration_status():
    return ctrl.migration_status()


@admin_bp.route("/migration/upgrade", methods=["POST"])
@roles_required("admin")
def migration_upgrade():
    return ctrl.migration_upgrade()


@admin_bp.route("/migration/downgrade", methods=["POST"])
@roles_required("admin")
def migration_downgrade():
    return ctrl.migration_downgrade()


@admin_bp.route("/seed-admin", methods=["POST"])
@roles_required("admin")
def seed_admin():
    return ctrl.seed_admin()


@admin_bp.route("/db-status", methods=["GET"])
@roles_required("admin")
def db_status():
    return ctrl.db_status()


@admin_bp.route("/analytics", methods=["GET"])
@roles_required("admin")
def analytics():
    return ctrl.get_analytics()


@admin_bp.route("/users", methods=["GET"])
@roles_required("admin")
def list_users():
    return user_ctrl.list_users()


@admin_bp.route("/users/test-candidates", methods=["GET"])
@roles_required("admin")
def test_account_candidates():
    return user_ctrl.test_account_candidates()


@admin_bp.route("/users/bulk-export", methods=["POST"])
@roles_required("admin")
def bulk_export_users():
    return user_ctrl.bulk_export()


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@roles_required("admin")
def get_user(user_id):
    return user_ctrl.get_user(user_id)


@admin_bp.route("/users/<int:user_id>/toggle-suspend", methods=["POST"])
@roles_required("admin")
def toggle_suspend_user(user_id):
    return user_ctrl.toggle_suspend(user_id)


@admin_bp.route("/users/<int:user_id>/status", methods=["PATCH"])
@roles_required("admin")
def update_user_status(user_id):
    return user_ctrl.update_status(user_id)


@admin_bp.route("/users/<int:user_id>/force-logout", methods=["POST"])
@roles_required("admin")
def force_logout_user(user_id):
    return user_ctrl.force_logout(user_id)


@admin_bp.route("/users/<int:user_id>/request-delete", methods=["POST"])
@roles_required("admin")
def request_delete_user(user_id):
    return user_ctrl.request_delete(user_id)


@admin_bp.route("/users/<int:user_id>/test-account", methods=["PATCH"])
@roles_required("admin")
def toggle_test_account(user_id):
    return user_ctrl.toggle_test_account(user_id)


@admin_bp.route("/export/<report_type>", methods=["GET"])
@roles_required("admin")
def export_report(report_type):
    return ctrl.export_report(report_type)


@admin_bp.route("/privacy/requests", methods=["GET"])
@roles_required("admin")
def list_privacy_requests():
    return privacy_ctrl.list_privacy_requests()


@admin_bp.route("/privacy/requests/<int:request_id>/complete", methods=["POST"])
@roles_required("admin")
def complete_privacy_request(request_id):
    return privacy_ctrl.complete_privacy_request_handler(request_id)


@admin_bp.route("/privacy/integrations", methods=["GET"])
@roles_required("admin")
def list_privacy_integrations():
    return privacy_ctrl.list_integration_audit()


@admin_bp.route("/privacy/consents/<int:user_id>", methods=["GET"])
@roles_required("admin")
def get_user_consents(user_id):
    return privacy_ctrl.get_user_consents(user_id)


@admin_bp.route("/education/videos", methods=["GET"])
@roles_required("admin")
def list_standalone_education_videos():
    from app.controllers import education_video_controller as education_video_ctrl

    return education_video_ctrl.list_admin_education_videos()


@admin_bp.route("/education/videos", methods=["POST"])
@roles_required("admin")
def create_standalone_education_video():
    from app.controllers import education_video_controller as education_video_ctrl

    return education_video_ctrl.create_admin_education_video()


@admin_bp.route("/education/videos/upload-signature", methods=["POST"])
@roles_required("admin")
def create_standalone_education_video_upload_signature():
    from app.controllers import education_video_controller as education_video_ctrl

    return education_video_ctrl.create_admin_education_video_upload_signature()


@admin_bp.route("/education/videos/<int:video_id>", methods=["PUT"])
@roles_required("admin")
def update_standalone_education_video(video_id):
    from app.controllers import education_video_controller as education_video_ctrl

    return education_video_ctrl.update_admin_education_video(video_id)


@admin_bp.route("/education/videos/<int:video_id>", methods=["DELETE"])
@roles_required("admin")
def delete_standalone_education_video(video_id):
    from app.controllers import education_video_controller as education_video_ctrl

    return education_video_ctrl.delete_admin_education_video(video_id)


@admin_bp.route("/education/<int:article_id>/video", methods=["POST"])
@roles_required("admin")
def upload_education_video(article_id):
    from app.controllers import education_controller as education_ctrl

    return education_ctrl.upload_education_resource_video(article_id)


@admin_bp.route("/education/<int:article_id>/video", methods=["DELETE"])
@roles_required("admin")
def delete_education_video(article_id):
    from app.controllers import education_controller as education_ctrl

    return education_ctrl.delete_education_resource_video(article_id)
