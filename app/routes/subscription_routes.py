from flask import Blueprint

from app.controllers import subscription_controller as ctrl
from app.middleware import roles_required

subscription_bp = Blueprint("subscriptions", __name__, url_prefix="/api/subscriptions")


@subscription_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_subscription():
    return ctrl.get_my_subscription()


@subscription_bp.route("/checkout", methods=["POST"])
@roles_required("user")
def checkout():
    return ctrl.checkout()


@subscription_bp.route("/webhook", methods=["POST"])
def webhook():
    return ctrl.webhook()
