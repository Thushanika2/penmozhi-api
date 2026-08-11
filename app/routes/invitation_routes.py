from flask import Blueprint

from app.controllers import cycle_share_controller as ctrl
from app.extensions import limiter
from app.middleware import roles_required

invitation_bp = Blueprint("invitations", __name__, url_prefix="/api/invitations")


@invitation_bp.post("/send")
@limiter.limit("5 per hour")
@roles_required("user")
def send_invitation():
    return ctrl.send_invitation()


@invitation_bp.post("/verify")
@limiter.limit("10 per minute")
@roles_required("user")
def verify_invitation():
    return ctrl.verify_invitation()


@invitation_bp.post("/resend")
@limiter.limit("5 per hour")
@roles_required("user")
def resend_invitation():
    return ctrl.resend_invitation()
