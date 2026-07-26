from flask import Blueprint

from app.controllers import perimenopause_log_controller as ctrl
from app.middleware import roles_required

perimenopause_log_bp = Blueprint(
    "perimenopause_logs",
    __name__,
    url_prefix="/api/perimenopause-logs",
)


@perimenopause_log_bp.route("", methods=["POST"])
@roles_required("user")
def create_perimenopause_log():
    return ctrl.create_perimenopause_log()


@perimenopause_log_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_perimenopause_logs():
    return ctrl.get_my_perimenopause_logs()


@perimenopause_log_bp.route("/<int:log_id>", methods=["PUT"])
@roles_required("user")
def update_perimenopause_log(log_id):
    return ctrl.update_perimenopause_log(log_id)
