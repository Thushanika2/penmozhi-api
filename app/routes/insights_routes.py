from flask import Blueprint

from app.controllers import insights_controller as ctrl
from app.middleware import roles_required

insights_bp = Blueprint("insights", __name__, url_prefix="/api/insights")


@insights_bp.route("", methods=["GET"])
@roles_required("user")
def get_insights():
    return ctrl.get_insights()
