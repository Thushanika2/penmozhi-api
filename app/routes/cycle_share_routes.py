from flask import Blueprint

from app.controllers import cycle_share_controller as ctrl
from app.middleware import roles_required
from app.extensions import limiter

cycle_share_bp = Blueprint("cycle_shares", __name__, url_prefix="/api/cycle-shares")


@cycle_share_bp.post("/invites")
@limiter.limit("5 per hour")
@roles_required("user")
def create_invite():
    return ctrl.create_invite()


@cycle_share_bp.post("/connect")
@limiter.limit("10 per minute")
@roles_required("user")
def connect_with_code():
    return ctrl.connect_with_code()


@cycle_share_bp.get("/connections")
@roles_required("user")
def list_connections():
    return ctrl.list_connections()


@cycle_share_bp.post("/connections/<int:connection_id>/disconnect")
@roles_required("user")
def disconnect(connection_id):
    return ctrl.disconnect(connection_id)


@cycle_share_bp.get("/connections/<int:connection_id>/view")
@roles_required("user")
def view_shared_cycle(connection_id):
    return ctrl.view_shared_cycle(connection_id)


@cycle_share_bp.route("", methods=["GET", "POST"])
@cycle_share_bp.route("/<int:_share_id>", methods=["DELETE"])
@cycle_share_bp.route("/<int:_share_id>/accept", methods=["POST"])
@cycle_share_bp.route("/<int:_share_id>/view", methods=["GET"])
@roles_required("user")
def legacy_cycle_share(_share_id=None):
    return ctrl.legacy_disabled()
