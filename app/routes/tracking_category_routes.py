from flask import Blueprint

from app.controllers import tracking_category_controller as ctrl
from app.middleware import roles_required

tracking_category_bp = Blueprint(
    "tracking_categories",
    __name__,
    url_prefix="/api/tracking-categories",
)


@tracking_category_bp.route("", methods=["GET"])
@roles_required("user")
def get_tracking_categories():
    return ctrl.get_tracking_categories()
