from flask import Blueprint

from app.controllers import pregnancy_profile_controller as ctrl
from app.middleware import roles_required

pregnancy_profile_bp = Blueprint(
    "pregnancy_profile",
    __name__,
    url_prefix="/api/pregnancy-profile",
)


@pregnancy_profile_bp.route("", methods=["GET"])
@roles_required("user")
def get_pregnancy_profile():
    return ctrl.get_pregnancy_profile()


@pregnancy_profile_bp.route("", methods=["PUT"])
@roles_required("user")
def upsert_pregnancy_profile():
    return ctrl.upsert_pregnancy_profile()
