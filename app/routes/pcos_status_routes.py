from flask import Blueprint

from app.controllers import pcos_status_controller as ctrl
from app.middleware import roles_required

pcos_status_bp = Blueprint("pcos_status", __name__, url_prefix="/api/pcos-status")


@pcos_status_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_pcos_status():
    return ctrl.get_my_pcos_status()


@pcos_status_bp.route("/<int:status_id>", methods=["PUT"])
@roles_required("user", "admin")
def update_pcos_status(status_id):
    return ctrl.update_pcos_status(status_id)


@pcos_status_bp.route("/<int:status_id>/history", methods=["GET"])
@roles_required("user")
def get_pcos_status_history(status_id):
    return ctrl.get_pcos_status_history(status_id)
