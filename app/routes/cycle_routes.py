from flask import Blueprint

from app.controllers import cycle_controller as ctrl
from app.middleware import roles_required

cycle_bp = Blueprint("cycles", __name__, url_prefix="/api/cycles")


@cycle_bp.route("", methods=["POST"])
@roles_required("user")
def create_cycle():
    return ctrl.create_cycle()


@cycle_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_cycles():
    return ctrl.get_my_cycles()


@cycle_bp.route("/predict-next", methods=["GET"])
@roles_required("user")
def predict_next_period():
    return ctrl.predict_next_period()


@cycle_bp.route("/insights", methods=["GET"])
@roles_required("user")
def get_cycle_insights():
    return ctrl.get_cycle_insights()


@cycle_bp.route("/calendar", methods=["GET"])
@roles_required("user")
def get_calendar():
    return ctrl.get_calendar()


@cycle_bp.route("/<int:cycle_id>", methods=["PUT"])
@roles_required("user")
def update_cycle(cycle_id):
    return ctrl.update_cycle(cycle_id)


@cycle_bp.route("/<int:cycle_id>", methods=["DELETE"])
@roles_required("user")
def delete_cycle(cycle_id):
    return ctrl.delete_cycle(cycle_id)
