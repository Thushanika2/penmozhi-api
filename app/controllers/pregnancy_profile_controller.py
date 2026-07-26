from datetime import date, timedelta

from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.pregnancy_profile_model import PregnancyProfile
from app.utils import parse_date, utc_now


def _compute_trimester(lmp: date, reference: date | None = None) -> int:
    reference = reference or date.today()
    weeks = (reference - lmp).days // 7
    if weeks < 13:
        return 1
    if weeks < 27:
        return 2
    return 3


def _compute_due_date(lmp: date) -> date:
    return lmp + timedelta(days=280)


def get_pregnancy_profile():
    profile = PregnancyProfile.query.filter_by(profile_id=current_user.id).first()
    if not profile:
        return jsonify({"pregnancy_profile": None}), 200
    return jsonify({"pregnancy_profile": profile.to_dict()}), 200


def _validate_pregnancy_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    if data.get("last_menstrual_period") is None:
        errors.append("last_menstrual_period is required.")
    else:
        try:
            parse_date(data.get("last_menstrual_period"))
        except ValueError:
            errors.append("last_menstrual_period must be a valid date.")

    return errors


def upsert_pregnancy_profile():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_pregnancy_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        lmp = parse_date(data.get("last_menstrual_period"))
        due = _compute_due_date(lmp)
        trimester = _compute_trimester(lmp)

        profile = PregnancyProfile.query.filter_by(profile_id=current_user.id).first()
        if profile:
            profile.last_menstrual_period = lmp
            profile.due_date = due
            profile.current_trimester = trimester
            profile.updated_at = utc_now()
        else:
            profile = PregnancyProfile(
                profile_id=current_user.id,
                last_menstrual_period=lmp,
                due_date=due,
                current_trimester=trimester,
            )
            db.session.add(profile)

        db.session.commit()
        return message_response(
            "pregnancy_profile.updated_success",
            "Pregnancy profile updated successfully.",
            200,
            pregnancy_profile=profile.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
