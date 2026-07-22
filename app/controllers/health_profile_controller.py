from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.utils import calculate_bmi


def _get_owned_health_profile(health_profile_id):
    health_profile = db.session.get(HealthProfile, health_profile_id)
    if not health_profile:
        return None, error_response("health.not_found", "Health profile not found.", 404)
    if current_user.role != "user" or health_profile.profile_id != current_user.id:
        return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    return health_profile, None


def _validate_health_profile_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    if "weight" in data and data.get("weight") is not None and str(data.get("weight")).strip() != "":
        try:
            weight = float(data.get("weight"))
            if weight <= 0:
                errors.append("weight must be a positive number.")
        except (TypeError, ValueError):
            errors.append("weight must be a number.")

    if "height" in data and data.get("height") is not None and str(data.get("height")).strip() != "":
        try:
            height = float(data.get("height"))
            if height <= 0:
                errors.append("height must be a positive number.")
        except (TypeError, ValueError):
            errors.append("height must be a number.")

    return errors


def get_health_profile(health_profile_id):
    health_profile, error = _get_owned_health_profile(health_profile_id)
    if error:
        return error
    return jsonify({"health_profile": health_profile.to_dict()}), 200


def update_health_profile(health_profile_id):
    health_profile, error = _get_owned_health_profile(health_profile_id)
    if error:
        return error

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_health_profile_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        if "weight" in data:
            value = data.get("weight")
            health_profile.weight = (
                float(value) if value is not None and str(value).strip() != "" else None
            )
        if "height" in data:
            value = data.get("height")
            health_profile.height = (
                float(value) if value is not None and str(value).strip() != "" else None
            )
        if "nutritional_needs" in data:
            value = data.get("nutritional_needs")
            health_profile.nutritional_needs = (
                str(value).strip() if value is not None and str(value).strip() != "" else None
            )
        if "health_risks" in data:
            value = data.get("health_risks")
            health_profile.health_risks = (
                str(value).strip() if value is not None and str(value).strip() != "" else None
            )

        health_profile.calculated_bmi = calculate_bmi(
            health_profile.weight,
            health_profile.height,
        )
        db.session.commit()

        return message_response(
            "health.updated_success",
            "Health profile updated successfully.",
            200,
            health_profile=health_profile.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_health_profile_risks(health_profile_id):
    health_profile, error = _get_owned_health_profile(health_profile_id)
    if error:
        return error

    risks = []
    if health_profile.health_risks:
        risks.append(health_profile.health_risks)

    bmi = health_profile.calculated_bmi
    bmi_category = None
    if bmi is not None:
        if bmi < 18.5:
            bmi_category = "underweight"
            risks.append("Underweight BMI — discuss nutrition with a clinician.")
        elif bmi < 25:
            bmi_category = "normal"
        elif bmi < 30:
            bmi_category = "overweight"
            risks.append("Overweight BMI — lifestyle and diet review recommended.")
        else:
            bmi_category = "obese"
            risks.append("Obese BMI — clinical follow-up recommended.")

    return jsonify({
        "health_profile_id": health_profile.id,
        "calculated_bmi": bmi,
        "bmi_category": bmi_category,
        "health_risks": health_profile.health_risks,
        "nutritional_needs": health_profile.nutritional_needs,
        "risks": risks,
    }), 200
