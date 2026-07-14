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
