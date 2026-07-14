from flask import Blueprint

from app.controllers import health_profile_controller as ctrl
from app.middleware import roles_required

health_profile_bp = Blueprint(
    "health_profiles",
    __name__,
    url_prefix="/api/health-profiles",
)


@health_profile_bp.route("/<int:health_profile_id>", methods=["GET"])
@roles_required("user")
def get_health_profile(health_profile_id):
    return ctrl.get_health_profile(health_profile_id)


@health_profile_bp.route("/<int:health_profile_id>", methods=["PUT"])
@roles_required("user")
def update_health_profile(health_profile_id):
    return ctrl.update_health_profile(health_profile_id)


@health_profile_bp.route("/<int:health_profile_id>/risks", methods=["GET"])
@roles_required("user")
def get_health_profile_risks(health_profile_id):
    return ctrl.get_health_profile_risks(health_profile_id)
