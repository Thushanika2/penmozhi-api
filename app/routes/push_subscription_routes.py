from flask import Blueprint

from app.controllers import push_subscription_controller as ctrl
from app.middleware import roles_required

push_subscription_bp = Blueprint(
    "push_subscriptions",
    __name__,
    url_prefix="/api/push-subscriptions",
)
push_api_bp = Blueprint("push_api", __name__, url_prefix="/api/push")


@push_subscription_bp.route("", methods=["POST"])
@roles_required("user")
def create_push_subscription():
    return ctrl.create_push_subscription()


@push_subscription_bp.route("/<int:subscription_id>", methods=["DELETE"])
@roles_required("user")
def delete_push_subscription(subscription_id):
    return ctrl.delete_push_subscription(subscription_id)


# Web Push friendly aliases. Keep the original routes for backwards compatibility.
@push_api_bp.route("/subscribe", methods=["POST"])
@roles_required("user")
def subscribe_push():
    return ctrl.create_push_subscription()


@push_api_bp.route("/unsubscribe", methods=["POST"])
@roles_required("user")
def unsubscribe_push():
    return ctrl.unsubscribe_push_subscription()
