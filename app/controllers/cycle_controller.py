from datetime import timedelta

from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.cycle_history_log_model import CycleHistoryLog
from app.utils import parse_date


def _validate_cycle_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    for field in ("cycle_start_date", "cycle_end_date", "flow_intensity"):
        if data.get(field) is None or str(data.get(field)).strip() == "":
            errors.append(f"{field} is required.")

    start = end = None
    try:
        if data.get("cycle_start_date"):
            start = parse_date(data.get("cycle_start_date"))
    except ValueError:
        errors.append("cycle_start_date must be a valid date (YYYY-MM-DD).")

    try:
        if data.get("cycle_end_date"):
            end = parse_date(data.get("cycle_end_date"))
    except ValueError:
        errors.append("cycle_end_date must be a valid date (YYYY-MM-DD).")

    if start and end and end < start:
        errors.append("cycle_end_date must be on or after cycle_start_date.")

    return errors


def _predict_next_period(profile_id, latest_start):
    cycles = (
        CycleHistoryLog.query.filter_by(profile_id=profile_id)
        .order_by(CycleHistoryLog.cycle_start_date.asc())
        .all()
    )
    if len(cycles) < 1:
        return latest_start + timedelta(days=28) if latest_start else None

    starts = [c.cycle_start_date for c in cycles]
    if latest_start and (not starts or starts[-1] != latest_start):
        starts.append(latest_start)

    if len(starts) < 2:
        return starts[-1] + timedelta(days=28)

    lengths = [(starts[i] - starts[i - 1]).days for i in range(1, len(starts))]
    avg_length = round(sum(lengths) / len(lengths))
    avg_length = max(21, min(avg_length, 45))
    return starts[-1] + timedelta(days=avg_length)


def create_cycle():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_cycle_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        start = parse_date(data.get("cycle_start_date"))
        end = parse_date(data.get("cycle_end_date"))
        predicted = _predict_next_period(current_user.id, start)

        cycle = CycleHistoryLog(
            profile_id=current_user.id,
            cycle_start_date=start,
            cycle_end_date=end,
            flow_intensity=str(data.get("flow_intensity")).strip(),
            notes=str(data.get("notes")).strip() if data.get("notes") else None,
            predicted_next_period_date=predicted,
        )
        db.session.add(cycle)
        db.session.commit()

        return message_response(
            "cycle.created_success",
            "Cycle entry created successfully.",
            201,
            cycle=cycle.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_my_cycles():
    cycles = (
        CycleHistoryLog.query.filter_by(profile_id=current_user.id)
        .order_by(CycleHistoryLog.cycle_start_date.desc())
        .all()
    )
    return jsonify({"cycles": [c.to_dict() for c in cycles]}), 200


def predict_next_period():
    from app.services.cycle_prediction_service import compute_cycle_insights

    insights = compute_cycle_insights(current_user)
    if not insights.get("has_data"):
        return jsonify({
            "predicted_next_period_date": None,
            "message": "Log at least one cycle to get a prediction.",
            "message_code": "cycle.log_at_least_one",
        }), 200

    return jsonify({
        "predicted_next_period_date": insights.get("next_period_date"),
        "ovulation_date": insights.get("ovulation_date"),
        "fertile_window_start": insights.get("fertile_window_start"),
        "fertile_window_end": insights.get("fertile_window_end"),
        "pms_window_start": insights.get("pms_window_start"),
        "pms_window_end": insights.get("pms_window_end"),
        "cycle_day": insights.get("cycle_day"),
        "current_phase": insights.get("current_phase"),
        "days_until_next_period": insights.get("days_until_next_period"),
        "based_on_cycles": insights.get("statistics", {}).get("logged_cycles", 0),
    }), 200


def get_cycle_insights():
    from app.services.cycle_prediction_service import compute_cycle_insights

    return jsonify(compute_cycle_insights(current_user)), 200


def update_cycle(cycle_id):
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    cycle = CycleHistoryLog.query.filter_by(id=cycle_id, profile_id=current_user.id).first()
    if not cycle:
        return error_response("cycle.not_found", "Cycle entry not found.", 404)

    errors = _validate_cycle_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        start = parse_date(data.get("cycle_start_date"))
        end = parse_date(data.get("cycle_end_date"))
        predicted = _predict_next_period(current_user.id, start)

        cycle.cycle_start_date = start
        cycle.cycle_end_date = end
        cycle.flow_intensity = str(data.get("flow_intensity")).strip()
        cycle.notes = str(data.get("notes")).strip() if data.get("notes") else None
        cycle.predicted_next_period_date = predicted
        db.session.commit()

        return message_response(
            "cycle.updated_success",
            "Cycle entry updated successfully.",
            200,
            cycle=cycle.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_cycle(cycle_id):
    cycle = CycleHistoryLog.query.filter_by(id=cycle_id, profile_id=current_user.id).first()
    if not cycle:
        return error_response("cycle.not_found", "Cycle entry not found.", 404)

    try:
        db.session.delete(cycle)
        db.session.commit()
        return message_response("cycle.deleted_success", "Cycle entry deleted successfully.", 200)
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_calendar():
    from app.controllers import daily_log_controller as daily_ctrl

    return daily_ctrl.get_calendar()
