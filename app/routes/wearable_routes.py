from flask import Blueprint

from app.controllers import wearable_controller as ctrl
from app.middleware import roles_required

wearable_bp = Blueprint("wearables", __name__, url_prefix="/api/wearables")


@wearable_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_wearables():
    return ctrl.get_my_wearables()


@wearable_bp.route("/<provider>/connect", methods=["GET"])
@roles_required("user")
def connect_wearable(provider):
    return ctrl.connect_wearable(provider)


@wearable_bp.route("/<provider>/callback", methods=["GET"])
@roles_required("user")
def callback_wearable(provider):
    return ctrl.callback_wearable(provider)


@wearable_bp.route("/<provider>/disconnect", methods=["DELETE"])
@roles_required("user")
def disconnect_wearable(provider):
    return ctrl.disconnect_wearable(provider)
