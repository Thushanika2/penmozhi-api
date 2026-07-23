import secrets
from datetime import timedelta

from flask import jsonify, request
from flask_jwt_extended import current_user
from marshmallow import ValidationError as MarshmallowValidationError

from app.api_responses import error_response, validation_errors
from app.extensions import db
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.schemas.onboarding_schema import OnboardingSchema
from app.utils import LANGUAGE_PREFERENCES


def _calculate_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100
    if height_m <= 0:
        return None
    return round(weight_kg / (height_m**2), 1)


def _predict_next_period(last_start, cycle_length):
    if not last_start:
        return None
    return last_start + timedelta(days=cycle_length)


def get_status():
    user = current_user
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    payload = {
        "onboarding_completed": user.onboarding_completed,
        "user": user.to_dict(),
    }
    if user.health_profile:
        payload["health_profile"] = user.health_profile.to_dict()
    return jsonify(payload), 200


def complete_onboarding():
    user = current_user
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    if user.onboarding_completed:
        return error_response("onboarding.already_completed", "Onboarding is already completed.", 409)

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    schema = OnboardingSchema()
    try:
        validated = schema.load(data)
    except MarshmallowValidationError as err:
        items = []
        for field, messages in err.messages.items():
            for message in messages:
                items.append((f"validation.{field}", str(message)))
        return validation_errors(items, 400)

    language = str(validated["language_preference"]).strip().lower()
    if language not in LANGUAGE_PREFERENCES:
        return validation_errors(
            [("validation.language_invalid", "language_preference must be 'tamil' or 'english'.")],
            400,
        )

    health_profile = user.health_profile
    if not health_profile:
        health_profile = HealthProfile(profile_id=user.id)
        db.session.add(health_profile)
        db.session.flush()

    try:
        bmi = _calculate_bmi(validated["weight"], validated["height"])

        user.full_name = validated["full_name"]
        user.date_of_birth = validated["date_of_birth"]
        user.country = validated["country"]
        user.timezone = validated["timezone"]
        user.language_preference = language

        health_profile.height = validated["height"]
        health_profile.weight = validated["weight"]
        health_profile.calculated_bmi = bmi
        health_profile.menarche_age = validated["menarche_age"]
        health_profile.average_cycle_length = validated["average_cycle_length"]
        health_profile.average_period_length = validated["average_period_length"]
        health_profile.last_period_start = validated["last_period_start"]
        health_profile.typical_flow = validated["typical_flow"]
        health_profile.cycle_regularity = validated["cycle_regularity"]
        health_profile.common_symptoms = validated["common_symptoms"]
        health_profile.health_conditions = validated["health_conditions"]
        health_profile.sleep_hours = validated["sleep_hours"]
        health_profile.water_intake_liters = validated["water_intake_liters"]
        health_profile.exercise_frequency = validated["exercise_frequency"]
        health_profile.stress_level = validated["stress_level"]
        health_profile.smoking = validated["smoking"]
        health_profile.alcohol = validated["alcohol"]
        health_profile.trying_to_conceive = validated["trying_to_conceive"]
        health_profile.is_pregnant = validated["is_pregnant"]
        health_profile.is_breastfeeding = validated["is_breastfeeding"]
        health_profile.using_birth_control = validated["using_birth_control"]
        health_profile.birth_control_type = validated["birth_control_type"]
        health_profile.notify_period = validated["notify_period"]
        health_profile.notify_ovulation = validated["notify_ovulation"]
        health_profile.notify_medication = validated["notify_medication"]
        health_profile.notify_daily_health = validated["notify_daily_health"]

        if "pcos" in validated["health_conditions"]:
            pcos = PCOSDisorderStatus.query.filter_by(health_profile_id=health_profile.id).first()
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

        period_end = validated["last_period_start"] + timedelta(
            days=validated["average_period_length"] - 1
        )
        predicted_next = _predict_next_period(
            validated["last_period_start"],
            validated["average_cycle_length"],
        )

        existing_cycle = (
            CycleHistoryLog.query.filter_by(profile_id=user.id)
            .order_by(CycleHistoryLog.cycle_start_date.desc())
            .first()
        )
        if not existing_cycle:
            db.session.add(
                CycleHistoryLog(
                    profile_id=user.id,
                    cycle_start_date=validated["last_period_start"],
                    cycle_end_date=period_end,
                    flow_intensity=validated["typical_flow"],
                    predicted_next_period_date=predicted_next,
                )
            )

        user.onboarding_completed = True
        db.session.commit()

        return jsonify(
            {
                "message_code": "onboarding.completed",
                "message": "Onboarding completed successfully.",
                "user": user.to_dict(),
                "health_profile": health_profile.to_dict(),
            }
        ), 200
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)

