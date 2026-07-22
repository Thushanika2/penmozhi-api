from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.utils import parse_date


def _user_health_profile():
    return HealthProfile.query.filter_by(profile_id=current_user.id).first()


def _get_accessible_status(status_id):
    status = db.session.get(PCOSDisorderStatus, status_id)
    if not status:
        return None, error_response("pcos.not_found", "PCOS disorder status not found.", 404)

    health = db.session.get(HealthProfile, status.health_profile_id)
    if not health:
        return None, error_response("pcos.not_found", "PCOS disorder status not found.", 404)

    if current_user.role == "admin":
        return status, None

    if current_user.role == "user" and health.profile_id == current_user.id:
        return status, None

    return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)


def get_my_pcos_status():
    health = _user_health_profile()
    if not health:
        return error_response("health.not_found", "Health profile not found.", 404)

    statuses = (
        PCOSDisorderStatus.query.filter_by(health_profile_id=health.id)
        .order_by(PCOSDisorderStatus.created_at.desc())
        .all()
    )
    return jsonify({"pcos_statuses": [s.to_dict() for s in statuses]}), 200


def update_pcos_status(status_id):
    status, error = _get_accessible_status(status_id)
    if error:
        return error

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = []
    if "diagnosed_date" in data and data.get("diagnosed_date"):
        try:
            parse_date(data.get("diagnosed_date"))
        except ValueError:
            errors.append("diagnosed_date must be a valid date (YYYY-MM-DD).")
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        disorder_type = status.disorder_type
        diagnosis_status = status.diagnosis_status
        diagnosed_date = status.diagnosed_date

        if "disorder_type" in data and data.get("disorder_type") is not None:
            disorder_type = str(data.get("disorder_type")).strip()
        if "diagnosis_status" in data and data.get("diagnosis_status") is not None:
            diagnosis_status = str(data.get("diagnosis_status")).strip()
        if "diagnosed_date" in data:
            value = data.get("diagnosed_date")
            diagnosed_date = parse_date(value) if value else None

        # New row becomes the current status; older rows form history
        updated = PCOSDisorderStatus(
            health_profile_id=status.health_profile_id,
            disorder_type=disorder_type,
            diagnosis_status=diagnosis_status,
            diagnosed_date=diagnosed_date,
        )
        db.session.add(updated)
        db.session.commit()
        return message_response(
            "pcos.updated_success",
            "PCOS disorder status updated successfully.",
            200,
            pcos_status=updated.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_pcos_status_history(status_id):
    status, error = _get_accessible_status(status_id)
    if error:
        return error

    history = (
        PCOSDisorderStatus.query.filter_by(health_profile_id=status.health_profile_id)
        .order_by(PCOSDisorderStatus.created_at.desc())
        .all()
    )
    return jsonify({
        "pcos_status": status.to_dict(),
        "history": [h.to_dict() for h in history],
    }), 200
