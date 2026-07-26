from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.perimenopause_log_model import PerimenopauseLog
from app.utils import parse_date


def _get_owned_perimenopause_log(log_id):
    log = db.session.get(PerimenopauseLog, log_id)
    if not log:
        return None, error_response("perimenopause_logs.not_found", "Perimenopause log not found.", 404)
    if log.profile_id != current_user.id:
        return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    return log, None


def _validate_perimenopause_payload(data, log_id=None):
    errors = []
    if not data:
        return ["Request body is required."]

    if log_id is None and data.get("log_date") is None:
        errors.append("log_date is required.")
    if "log_date" in data and data.get("log_date") is not None:
        try:
            parse_date(data.get("log_date"))
        except ValueError:
            errors.append("log_date must be a valid date.")

    return errors


def create_perimenopause_log():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_perimenopause_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    log_date = parse_date(data.get("log_date"))
    existing = PerimenopauseLog.query.filter_by(
        profile_id=current_user.id,
        log_date=log_date,
    ).first()
    if existing:
        return validation_errors(
            [("validation.log_date_exists", "A log already exists for this date.")],
            400,
        )

    try:
        log = PerimenopauseLog(
            profile_id=current_user.id,
            log_date=log_date,
            hot_flashes=bool(data.get("hot_flashes", False)),
            night_sweats=bool(data.get("night_sweats", False)),
            mood_changes=str(data.get("mood_changes")).strip() if data.get("mood_changes") else None,
            sleep_disruption=bool(data.get("sleep_disruption", False)),
            notes=str(data.get("notes")).strip() if data.get("notes") else None,
        )
        db.session.add(log)
        db.session.commit()
        return message_response(
            "perimenopause_logs.created_success",
            "Perimenopause log created successfully.",
            201,
            perimenopause_log=log.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_my_perimenopause_logs():
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    query = PerimenopauseLog.query.filter_by(profile_id=current_user.id)
    if from_date:
        try:
            query = query.filter(PerimenopauseLog.log_date >= parse_date(from_date))
        except ValueError:
            return validation_errors([("validation.from", "Invalid from date.")], 400)
    if to_date:
        try:
            query = query.filter(PerimenopauseLog.log_date <= parse_date(to_date))
        except ValueError:
            return validation_errors([("validation.to", "Invalid to date.")], 400)

    logs = query.order_by(PerimenopauseLog.log_date.desc()).all()
    return jsonify({"perimenopause_logs": [log.to_dict() for log in logs]}), 200


def update_perimenopause_log(log_id):
    log, error = _get_owned_perimenopause_log(log_id)
    if error:
        return error

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_perimenopause_payload(data, log_id=log_id)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        if "log_date" in data and data.get("log_date") is not None:
            new_date = parse_date(data.get("log_date"))
            duplicate = PerimenopauseLog.query.filter(
                PerimenopauseLog.profile_id == current_user.id,
                PerimenopauseLog.log_date == new_date,
                PerimenopauseLog.id != log.id,
            ).first()
            if duplicate:
                return validation_errors(
                    [("validation.log_date_exists", "A log already exists for this date.")],
                    400,
                )
            log.log_date = new_date
        if "hot_flashes" in data:
            log.hot_flashes = bool(data.get("hot_flashes"))
        if "night_sweats" in data:
            log.night_sweats = bool(data.get("night_sweats"))
        if "mood_changes" in data:
            log.mood_changes = (
                str(data.get("mood_changes")).strip() if data.get("mood_changes") else None
            )
        if "sleep_disruption" in data:
            log.sleep_disruption = bool(data.get("sleep_disruption"))
        if "notes" in data:
            log.notes = str(data.get("notes")).strip() if data.get("notes") else None

        db.session.commit()
        return message_response(
            "perimenopause_logs.updated_success",
            "Perimenopause log updated successfully.",
            200,
            perimenopause_log=log.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
