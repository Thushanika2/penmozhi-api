from datetime import timedelta

from flask import jsonify, request
from flask_jwt_extended import current_user

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
        return jsonify({"error": "Request body is required."}), 400

    errors = _validate_cycle_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        start = parse_date(data.get("cycle_start_date"))
        end = parse_date(data.get("cycle_end_date"))
        predicted = _predict_next_period(current_user.id, start)

        cycle = CycleHistoryLog(
            profile_id=current_user.id,
            cycle_start_date=start,
            cycle_end_date=end,
            flow_intensity=str(data.get("flow_intensity")).strip(),
            predicted_next_period_date=predicted,
        )
        db.session.add(cycle)
        db.session.commit()

        return jsonify({
            "message": "Cycle entry created successfully.",
            "cycle": cycle.to_dict(),
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "An internal server error occurred."}), 500


def get_my_cycles():
    cycles = (
        CycleHistoryLog.query.filter_by(profile_id=current_user.id)
        .order_by(CycleHistoryLog.cycle_start_date.desc())
        .all()
    )
    return jsonify({"cycles": [c.to_dict() for c in cycles]}), 200


def predict_next_period():
    cycles = (
        CycleHistoryLog.query.filter_by(profile_id=current_user.id)
        .order_by(CycleHistoryLog.cycle_start_date.desc())
        .all()
    )
    if not cycles:
        return jsonify({
            "predicted_next_period_date": None,
            "message": "Log at least one cycle to get a prediction.",
        }), 200

    latest = cycles[0]
    predicted = latest.predicted_next_period_date or _predict_next_period(
        current_user.id,
        latest.cycle_start_date,
    )
    return jsonify({
        "predicted_next_period_date": predicted.isoformat() if predicted else None,
        "based_on_cycles": len(cycles),
        "latest_cycle": latest.to_dict(),
    }), 200
