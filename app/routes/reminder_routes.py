from flask import Blueprint

from app.controllers import reminder_controller as ctrl
from app.middleware import roles_required

reminder_bp = Blueprint("reminders", __name__, url_prefix="/api/reminders")


@reminder_bp.route("", methods=["POST"])
@roles_required("user")
def create_reminder():
    return ctrl.create_reminder()


@reminder_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_reminders():
    return ctrl.get_my_reminders()


@reminder_bp.route("/<int:reminder_id>", methods=["PUT"])
@roles_required("user")
def update_reminder(reminder_id):
    return ctrl.update_reminder(reminder_id)


@reminder_bp.route("/<int:reminder_id>/mark-taken", methods=["POST"])
@roles_required("user")
def mark_reminder_taken(reminder_id):
    return ctrl.mark_reminder_taken(reminder_id)


@reminder_bp.route("/<int:reminder_id>/snooze", methods=["POST"])
@roles_required("user")
def snooze_reminder(reminder_id):
    return ctrl.snooze_reminder(reminder_id)


@reminder_bp.route("/<int:reminder_id>", methods=["DELETE"])
@roles_required("user")
def delete_reminder(reminder_id):
    return ctrl.delete_reminder(reminder_id)
