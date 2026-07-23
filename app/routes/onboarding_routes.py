from flask import Blueprint

from app.controllers import onboarding_controller as ctrl
from app.middleware import jwt_required_user

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/api/onboarding")


@onboarding_bp.route("/status", methods=["GET"])
@jwt_required_user
def status():
    return ctrl.get_status()


@onboarding_bp.route("/complete", methods=["POST"])
@jwt_required_user
def complete():
    return ctrl.complete_onboarding()
