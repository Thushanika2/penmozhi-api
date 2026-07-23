from flask import Blueprint

from app.controllers import dashboard_controller as ctrl
from app.middleware import roles_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/summary", methods=["GET"])
@roles_required("user")
def summary():
    return ctrl.get_summary()
