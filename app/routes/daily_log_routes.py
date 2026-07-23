from flask import Blueprint

from app.controllers import daily_log_controller as ctrl
from app.middleware import roles_required

daily_log_bp = Blueprint("daily_logs", __name__, url_prefix="/api/daily-logs")


@daily_log_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_logs():
    return ctrl.get_my_logs()


@daily_log_bp.route("/date/<log_date>", methods=["GET"])
@roles_required("user")
def get_by_date(log_date):
    return ctrl.get_log_by_date(log_date)


@daily_log_bp.route("", methods=["POST"])
@roles_required("user")
def upsert_log():
    return ctrl.upsert_log()


@daily_log_bp.route("/<int:log_id>", methods=["PUT"])
@roles_required("user")
def update_log(log_id):
    return ctrl.update_log(log_id)


@daily_log_bp.route("/<int:log_id>", methods=["DELETE"])
@roles_required("user")
def delete_log(log_id):
    return ctrl.delete_log(log_id)
