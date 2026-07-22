from datetime import datetime, timedelta

from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.utils import parse_time


def _get_owned_reminder(reminder_id):
    reminder = db.session.get(MedicationSupplementReminder, reminder_id)
    if not reminder:
        return None, error_response("reminders.not_found", "Reminder not found.", 404)
    if reminder.profile_id != current_user.id:
        return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    return reminder, None


def _validate_reminder_payload(data, reminder_id=None):
    errors = []
    if not data:
        return ["Request body is required."]

    required_on_create = ("item_name", "reminder_type", "scheduled_time")
    if reminder_id is None:
        for field in required_on_create:
            if data.get(field) is None or str(data.get(field)).strip() == "":
                errors.append(f"{field} is required.")

    if "scheduled_time" in data and data.get("scheduled_time") is not None:
        try:
            parse_time(data.get("scheduled_time"))
        except (TypeError, ValueError):
            errors.append("scheduled_time must be a valid time (HH:MM or HH:MM:SS).")

    return errors


def create_reminder():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_reminder_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        reminder = MedicationSupplementReminder(
            profile_id=current_user.id,
            item_name=str(data.get("item_name")).strip(),
            reminder_type=str(data.get("reminder_type")).strip(),
            scheduled_time=parse_time(data.get("scheduled_time")),
            dosage=str(data.get("dosage")).strip() if data.get("dosage") else None,
            adherence_status=str(data.get("adherence_status", "pending")).strip() or "pending",
        )
        db.session.add(reminder)
        db.session.commit()

        return message_response(
            "reminders.created_success",
            "Reminder created successfully.",
            201,
            reminder=reminder.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_my_reminders():
    reminders = (
        MedicationSupplementReminder.query.filter_by(profile_id=current_user.id)
        .order_by(MedicationSupplementReminder.scheduled_time.asc())
        .all()
    )
    return jsonify({"reminders": [r.to_dict() for r in reminders]}), 200


def update_reminder(reminder_id):
    reminder, error = _get_owned_reminder(reminder_id)
    if error:
        return error

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_reminder_payload(data, reminder_id=reminder_id)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        if "item_name" in data and data.get("item_name") is not None:
            reminder.item_name = str(data.get("item_name")).strip()
        if "reminder_type" in data and data.get("reminder_type") is not None:
            reminder.reminder_type = str(data.get("reminder_type")).strip()
        if "scheduled_time" in data and data.get("scheduled_time") is not None:
            reminder.scheduled_time = parse_time(data.get("scheduled_time"))
        if "dosage" in data:
            reminder.dosage = (
                str(data.get("dosage")).strip() if data.get("dosage") else None
            )
        if "adherence_status" in data and data.get("adherence_status") is not None:
            reminder.adherence_status = str(data.get("adherence_status")).strip()

        db.session.commit()
        return message_response(
            "reminders.updated_success",
            "Reminder updated successfully.",
            200,
            reminder=reminder.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def mark_reminder_taken(reminder_id):
    reminder, error = _get_owned_reminder(reminder_id)
    if error:
        return error

    try:
        reminder.adherence_status = "taken"
        db.session.commit()
        return message_response(
            "reminders.marked_taken",
            "Reminder marked as taken.",
            200,
            reminder=reminder.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def snooze_reminder(reminder_id):
    reminder, error = _get_owned_reminder(reminder_id)
    if error:
        return error

    data = request.get_json(silent=True) or {}
    minutes = data.get("minutes", 10)
    try:
        minutes = int(minutes)
        if minutes <= 0:
            return error_response("validation.minutes_positive", "minutes must be a positive integer.", 400)
    except (TypeError, ValueError):
        return error_response("validation.minutes_positive", "minutes must be a positive integer.", 400)

    try:
        base = datetime.combine(datetime.today().date(), reminder.scheduled_time)
        new_time = (base + timedelta(minutes=minutes)).time()
        reminder.scheduled_time = new_time
        reminder.adherence_status = "snoozed"
        db.session.commit()
        return message_response(
            "reminders.snoozed",
            f"Reminder snoozed by {minutes} minutes.",
            200,
            reminder=reminder.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_reminder(reminder_id):
    reminder, error = _get_owned_reminder(reminder_id)
    if error:
        return error

    try:
        db.session.delete(reminder)
        db.session.commit()
        return message_response("reminders.deleted_success", "Reminder deleted successfully.", 200)
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
