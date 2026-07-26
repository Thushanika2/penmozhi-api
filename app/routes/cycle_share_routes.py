from flask import Blueprint

from app.controllers import cycle_share_controller as ctrl
from app.middleware import roles_required

cycle_share_bp = Blueprint("cycle_shares", __name__, url_prefix="/api/cycle-shares")


@cycle_share_bp.route("", methods=["POST"])
@roles_required("user")
def create_cycle_share():
    return ctrl.create_cycle_share()


@cycle_share_bp.route("", methods=["GET"])
@roles_required("user")
def list_cycle_shares():
    return ctrl.list_cycle_shares()


@cycle_share_bp.route("/<int:share_id>/accept", methods=["POST"])
@roles_required("user")
def accept_cycle_share(share_id):
    return ctrl.accept_cycle_share(share_id)


@cycle_share_bp.route("/<int:share_id>", methods=["DELETE"])
@roles_required("user")
def delete_cycle_share(share_id):
    return ctrl.delete_cycle_share(share_id)


@cycle_share_bp.route("/<int:share_id>/view", methods=["GET"])
@roles_required("user")
def view_cycle_share(share_id):
    return ctrl.view_cycle_share(share_id)
