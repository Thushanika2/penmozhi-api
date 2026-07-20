from flask import Blueprint

from app.controllers import admin_controller as ctrl
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
