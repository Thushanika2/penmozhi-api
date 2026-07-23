from flask import jsonify, request
from flask_jwt_extended import current_user
from marshmallow import ValidationError as MarshmallowValidationError

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.schemas.profile_schema import HealthProfileSettingsSchema
from app.utils import calculate_bmi


def _get_owned_health_profile(health_profile_id):
    health_profile = db.session.get(HealthProfile, health_profile_id)
    if not health_profile:
        return None, error_response("health.not_found", "Health profile not found.", 404)
    if current_user.role != "user" or health_profile.profile_id != current_user.id:
        return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    return health_profile, None


def _schema_errors(schema_err):
    return validation_errors(
        [("validation.invalid_payload", str(msg)) for msgs in schema_err.messages.values() for msg in msgs],
        400,
    )


def _apply_health_profile_fields(health_profile, validated):
    simple_fields = [
        "weight",
        "height",
        "nutritional_needs",
        "health_risks",
        "menarche_age",
        "average_cycle_length",
        "average_period_length",
        "last_period_start",
        "typical_flow",
        "cycle_regularity",
        "sleep_hours",
        "water_intake_liters",
        "exercise_frequency",
        "stress_level",
        "birth_control_type",
    ]
    for field in simple_fields:
        if field in validated:
            setattr(health_profile, field, validated[field])

    bool_fields = [
        "smoking",
        "alcohol",
        "trying_to_conceive",
        "is_pregnant",
        "is_breastfeeding",
        "using_birth_control",
        "notify_period",
        "notify_ovulation",
        "notify_medication",
        "notify_daily_health",
    ]
    for field in bool_fields:
        if field in validated:
            setattr(health_profile, field, validated[field])

    if "common_symptoms" in validated:
        health_profile.common_symptoms = validated["common_symptoms"]
    if "health_conditions" in validated:
        health_profile.health_conditions = validated["health_conditions"]

    health_profile.calculated_bmi = calculate_bmi(health_profile.weight, health_profile.height)

    if "health_conditions" in validated:
        conditions = validated["health_conditions"] or []
        pcos = PCOSDisorderStatus.query.filter_by(health_profile_id=health_profile.id).first()
        if "pcos" in conditions:
            if pcos:
                pcos.disorder_type = "pcos"
                pcos.diagnosis_status = "diagnosed"
            else:
                db.session.add(
                    PCOSDisorderStatus(
                        health_profile_id=health_profile.id,
                        disorder_type="pcos",
                        diagnosis_status="diagnosed",
                    )
                )
        elif pcos and pcos.disorder_type == "pcos":
            pcos.disorder_type = "none"
            pcos.diagnosis_status = "not_diagnosed"


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

    schema = HealthProfileSettingsSchema()
    try:
        validated = schema.load(data, partial=True)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    if not validated:
        return validation_errors(
            [("validation.no_fields", "At least one health profile field is required.")],
            400,
        )

    try:
        _apply_health_profile_fields(health_profile, validated)
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
