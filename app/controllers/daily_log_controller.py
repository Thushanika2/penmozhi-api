from calendar import monthrange
from datetime import date, timedelta

from flask import jsonify, request
from flask_jwt_extended import current_user
from marshmallow import ValidationError as MarshmallowValidationError

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.daily_log_model import DailyLog
from app.schemas.daily_log_schema import DailyLogSchema, DailyLogUpdateSchema
from app.services.cycle_prediction_service import compute_cycle_insights
from app.utils import parse_date


def _schema_errors(err):
    items = []
    for field, messages in err.messages.items():
        for message in messages:
            items.append((f"validation.{field}", str(message)))
    return validation_errors(items, 400)


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _iter_dates(start: date, end: date):
    return [d.isoformat() for d in _date_range(start, end)]


def get_my_logs():
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    query = DailyLog.query.filter_by(profile_id=current_user.id)
    if from_date:
        try:
            query = query.filter(DailyLog.log_date >= parse_date(from_date))
        except ValueError:
            return validation_errors([("validation.from", "Invalid from date.")], 400)
    if to_date:
        try:
            query = query.filter(DailyLog.log_date <= parse_date(to_date))
        except ValueError:
            return validation_errors([("validation.to", "Invalid to date.")], 400)

    logs = query.order_by(DailyLog.log_date.desc()).all()
    return jsonify({"daily_logs": [log.to_dict() for log in logs]}), 200


def get_log_by_date(log_date_str):
    try:
        log_date = parse_date(log_date_str)
    except ValueError:
        return validation_errors([("validation.log_date", "Invalid date.")], 400)

    log = DailyLog.query.filter_by(profile_id=current_user.id, log_date=log_date).first()
    if not log:
        return jsonify({"daily_log": None}), 200
    return jsonify({"daily_log": log.to_dict()}), 200


def upsert_log():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    schema = DailyLogSchema()
    try:
        validated = schema.load(data)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    log_date = validated["log_date"]
    existing = DailyLog.query.filter_by(profile_id=current_user.id, log_date=log_date).first()

    try:
        if existing:
            for key, value in validated.items():
                setattr(existing, key, value)
            db.session.commit()
            return message_response(
                "daily_log.updated",
                "Daily log updated successfully.",
                200,
                daily_log=existing.to_dict(),
            )

        log = DailyLog(profile_id=current_user.id, **validated)
        db.session.add(log)
        db.session.commit()
        return message_response(
            "daily_log.created",
            "Daily log created successfully.",
            201,
            daily_log=log.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def update_log(log_id):
    log = DailyLog.query.filter_by(id=log_id, profile_id=current_user.id).first()
    if not log:
        return error_response("daily_log.not_found", "Daily log not found.", 404)

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    schema = DailyLogUpdateSchema()
    try:
        validated = schema.load(data, partial=True)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    try:
        for key, value in validated.items():
            setattr(log, key, value)
        db.session.commit()
        return message_response(
            "daily_log.updated",
            "Daily log updated successfully.",
            200,
            daily_log=log.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_log(log_id):
    log = DailyLog.query.filter_by(id=log_id, profile_id=current_user.id).first()
    if not log:
        return error_response("daily_log.not_found", "Daily log not found.", 404)

    try:
        db.session.delete(log)
        db.session.commit()
        return message_response("daily_log.deleted", "Daily log deleted successfully.", 200)
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def _calendar_reference_date(year: int, month: int) -> date:
    """Pick a reference date so cycle predictions match the month being viewed."""
    today = date.today()
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    if month_start <= today <= month_end:
        return today
    if month_end < today:
        return month_end
    return month_start


def get_calendar():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not year or not month or month < 1 or month > 12:
        return validation_errors([("validation.month", "year and month are required.")], 400)

    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    reference_date = _calendar_reference_date(year, month)

    cycles = current_user.cycle_history_logs or []
    period_days = set()
    for cycle in cycles:
        if cycle.cycle_end_date and cycle.cycle_start_date:
            for d in _date_range(cycle.cycle_start_date, cycle.cycle_end_date):
                if month_start <= d <= month_end:
                    period_days.add(d.isoformat())

    insights = compute_cycle_insights(current_user, reference_date)
    predicted_period = set()
    fertile_days = set()
    ovulation_days = set()
    pms_days = set()

    if insights.get("has_data"):
        if insights.get("next_period_date"):
            next_period = parse_date(insights["next_period_date"])
            period_len = insights.get("average_period_length") or 5
            pred_start = next_period
            pred_end = next_period + timedelta(days=period_len - 1)
            for d in _date_range(pred_start, pred_end):
                if month_start <= d <= month_end:
                    predicted_period.add(d.isoformat())

        if insights.get("ovulation_date"):
            ov = parse_date(insights["ovulation_date"])
            if month_start <= ov <= month_end:
                ovulation_days.add(ov.isoformat())

        if insights.get("fertile_window_start") and insights.get("fertile_window_end"):
            fs = parse_date(insights["fertile_window_start"])
            fe = parse_date(insights["fertile_window_end"])
            for d in _date_range(fs, fe):
                if month_start <= d <= month_end:
                    fertile_days.add(d.isoformat())

        if insights.get("pms_window_start") and insights.get("pms_window_end"):
            ps = parse_date(insights["pms_window_start"])
            pe = parse_date(insights["pms_window_end"])
            for d in _date_range(ps, pe):
                if month_start <= d <= month_end:
                    pms_days.add(d.isoformat())

    logs = (
        DailyLog.query.filter(
            DailyLog.profile_id == current_user.id,
            DailyLog.log_date >= month_start,
            DailyLog.log_date <= month_end,
        )
        .all()
    )

    return jsonify(
        {
            "year": year,
            "month": month,
            "period_days": sorted(period_days),
            "predicted_period_days": sorted(predicted_period),
            "fertile_days": sorted(fertile_days),
            "ovulation_days": sorted(ovulation_days),
            "pms_days": sorted(pms_days),
            "daily_logs": [log.to_dict() for log in logs],
            "insights": insights,
        }
    ), 200
