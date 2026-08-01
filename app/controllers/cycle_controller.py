from datetime import timedelta

from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.cycle_history_log_model import CycleHistoryLog
from app.services.cycle_prediction_service import (
    GAP_REASON_CHOICES,
    UNUSUAL_GAP_DAYS,
    cycle_gaps_from_starts,
    estimate_cycle_length,
    filter_typical_lengths,
    find_unusual_gap_with_previous,
)
from app.utils import parse_date


def _validate_cycle_payload(data, *, require_gap_fields=False):
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

    gap_reason = data.get("gap_reason")
    if gap_reason is not None and str(gap_reason).strip():
        if str(gap_reason).strip() not in GAP_REASON_CHOICES:
            errors.append(
                "gap_reason must be one of: " + ", ".join(sorted(GAP_REASON_CHOICES))
            )

    if require_gap_fields:
        if not gap_reason or str(gap_reason).strip() not in GAP_REASON_CHOICES:
            errors.append("gap_reason is required when the gap between periods is unusual.")

    prior_periods = data.get("prior_periods") or []
    if prior_periods and not isinstance(prior_periods, list):
        errors.append("prior_periods must be a list.")
    else:
        for index, prior in enumerate(prior_periods or []):
            if not isinstance(prior, dict):
                errors.append(f"prior_periods[{index}] must be an object.")
                continue
            for field in ("cycle_start_date", "cycle_end_date", "flow_intensity"):
                if prior.get(field) is None or str(prior.get(field)).strip() == "":
                    errors.append(f"prior_periods[{index}].{field} is required.")
            try:
                p_start = parse_date(prior.get("cycle_start_date")) if prior.get("cycle_start_date") else None
                p_end = parse_date(prior.get("cycle_end_date")) if prior.get("cycle_end_date") else None
            except ValueError:
                errors.append(f"prior_periods[{index}] dates must be valid (YYYY-MM-DD).")
                continue
            if p_start and p_end and p_end < p_start:
                errors.append(
                    f"prior_periods[{index}].cycle_end_date must be on or after cycle_start_date."
                )
            if start and p_start and p_start >= start:
                errors.append(
                    f"prior_periods[{index}].cycle_start_date must be before the new period start."
                )
            prior_gap_reason = prior.get("gap_reason")
            if prior_gap_reason is not None and str(prior_gap_reason).strip():
                if str(prior_gap_reason).strip() not in GAP_REASON_CHOICES:
                    errors.append(
                        f"prior_periods[{index}].gap_reason must be one of: "
                        + ", ".join(sorted(GAP_REASON_CHOICES))
                    )

    return errors


def _existing_starts(profile_id, exclude_id=None):
    query = CycleHistoryLog.query.filter_by(profile_id=profile_id)
    if exclude_id is not None:
        query = query.filter(CycleHistoryLog.id != exclude_id)
    cycles = query.order_by(CycleHistoryLog.cycle_start_date.asc()).all()
    return [c.cycle_start_date for c in cycles]


def _predict_next_period(profile_id, anchor_start, extra_starts=None, exclude_id=None):
    """Predict the next period after anchor_start using typical cycle length."""
    if not anchor_start:
        return None

    starts = _existing_starts(profile_id, exclude_id=exclude_id)
    if anchor_start not in starts:
        starts.append(anchor_start)
    if extra_starts:
        for start in extra_starts:
            if start and start not in starts:
                starts.append(start)

    starts = sorted(starts)
    health = getattr(current_user, "health_profile", None)
    default_cycle = health.average_cycle_length if health and health.average_cycle_length else 28
    avg_length, _meta = estimate_cycle_length(starts, default_cycle)
    return anchor_start + timedelta(days=avg_length)


def _priors_resolve_unusual_gap(existing_starts, new_start, prior_starts):
    """
    Priors must either:
    - bridge the unusual gap so the immediate previous start is typical, or
    - add enough earlier history that at least one typical gap exists for predictions.
    """
    if not new_start or not prior_starts:
        return False

    unique_priors = []
    seen = set(existing_starts)
    for start in prior_starts:
        if not start or start >= new_start:
            return False
        if start in seen:
            continue
        seen.add(start)
        unique_priors.append(start)

    if not unique_priors:
        return False

    merged = sorted(seen)
    if find_unusual_gap_with_previous(merged, new_start) is None:
        return True

    history_gaps = cycle_gaps_from_starts(merged)
    return len(filter_typical_lengths(history_gaps)) >= 1


def _unusual_gap_response(gap_info, requires_prior_period=True):
    return (
        jsonify(
            {
                "error_code": "cycle.unusual_gap",
                "error": (
                    "Unusual gap detected between period dates. "
                    "Please explain the gap and add an earlier period date so predictions stay accurate."
                ),
                "gap_days": gap_info["gap_days"],
                "previous_start": gap_info["previous_start"].isoformat(),
                "new_start": gap_info["new_start"].isoformat(),
                "unusual_gap_threshold_days": UNUSUAL_GAP_DAYS,
                "requires_gap_reason": True,
                "requires_prior_period": requires_prior_period,
                "gap_reason_options": sorted(GAP_REASON_CHOICES),
            }
        ),
        422,
    )


def _parse_prior_periods(data):
    prior_periods = data.get("prior_periods") or []
    parsed = []
    for prior in prior_periods:
        gap_reason = (
            str(prior.get("gap_reason")).strip() if prior.get("gap_reason") else None
        )
        parsed.append(
            {
                "cycle_start_date": parse_date(prior.get("cycle_start_date")),
                "cycle_end_date": parse_date(prior.get("cycle_end_date")),
                "flow_intensity": str(prior.get("flow_intensity")).strip(),
                "notes": str(prior.get("notes")).strip() if prior.get("notes") else None,
                "gap_reason": gap_reason if gap_reason in GAP_REASON_CHOICES else None,
            }
        )
    return parsed


def create_cycle():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    try:
        start = parse_date(data.get("cycle_start_date")) if data.get("cycle_start_date") else None
    except ValueError:
        start = None

    existing_starts = _existing_starts(current_user.id)
    gap_info = find_unusual_gap_with_previous(existing_starts, start) if start else None
    gap_reason = str(data.get("gap_reason")).strip() if data.get("gap_reason") else None
    prior_periods_raw = data.get("prior_periods") or []

    if gap_info:
        has_reason = gap_reason in GAP_REASON_CHOICES
        prior_starts = []
        if isinstance(prior_periods_raw, list):
            for prior in prior_periods_raw:
                if not isinstance(prior, dict):
                    continue
                try:
                    prior_starts.append(parse_date(prior.get("cycle_start_date")))
                except (TypeError, ValueError):
                    continue
        resolved = _priors_resolve_unusual_gap(existing_starts, start, prior_starts)
        if not has_reason or not resolved:
            return _unusual_gap_response(gap_info, requires_prior_period=True)

    errors = _validate_cycle_payload(data, require_gap_fields=bool(gap_info))
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        start = parse_date(data.get("cycle_start_date"))
        end = parse_date(data.get("cycle_end_date"))
        prior_periods = _parse_prior_periods(data)
        extra_starts = [p["cycle_start_date"] for p in prior_periods]
        predicted = _predict_next_period(current_user.id, start, extra_starts=extra_starts)

        created = []
        for prior in prior_periods:
            # Skip duplicates that already exist
            exists = (
                CycleHistoryLog.query.filter_by(
                    profile_id=current_user.id,
                    cycle_start_date=prior["cycle_start_date"],
                ).first()
            )
            if exists:
                continue
            prior_predicted = _predict_next_period(
                current_user.id,
                prior["cycle_start_date"],
                extra_starts=extra_starts + [start],
            )
            prior_cycle = CycleHistoryLog(
                profile_id=current_user.id,
                cycle_start_date=prior["cycle_start_date"],
                cycle_end_date=prior["cycle_end_date"],
                flow_intensity=prior["flow_intensity"],
                notes=prior["notes"],
                gap_reason=prior["gap_reason"],
                predicted_next_period_date=prior_predicted,
            )
            db.session.add(prior_cycle)
            created.append(prior_cycle)

        cycle = CycleHistoryLog(
            profile_id=current_user.id,
            cycle_start_date=start,
            cycle_end_date=end,
            flow_intensity=str(data.get("flow_intensity")).strip(),
            notes=str(data.get("notes")).strip() if data.get("notes") else None,
            gap_reason=gap_reason,
            predicted_next_period_date=predicted,
        )
        db.session.add(cycle)
        db.session.commit()

        return message_response(
            "cycle.created_success",
            "Cycle entry created successfully.",
            201,
            cycle=cycle.to_dict(),
            prior_cycles=[c.to_dict() for c in created],
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

    quality = insights.get("prediction_quality") or {}
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
        "average_cycle_length": insights.get("average_cycle_length"),
        "based_on_cycles": insights.get("statistics", {}).get("typical_cycles_used", 0),
        "outlier_gaps_excluded": insights.get("statistics", {}).get("outlier_gaps_excluded", 0),
        "prediction_quality": quality,
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

    try:
        start = parse_date(data.get("cycle_start_date")) if data.get("cycle_start_date") else None
    except ValueError:
        start = None

    existing_starts = _existing_starts(current_user.id, exclude_id=cycle.id)
    gap_info = find_unusual_gap_with_previous(existing_starts, start) if start else None
    gap_reason = str(data.get("gap_reason")).strip() if data.get("gap_reason") else None
    prior_periods_raw = data.get("prior_periods") or []
    start_changed = start is not None and start != cycle.cycle_start_date

    if gap_info:
        if not gap_reason and cycle.gap_reason in GAP_REASON_CHOICES:
            gap_reason = cycle.gap_reason
        has_reason = gap_reason in GAP_REASON_CHOICES

        prior_starts = []
        if isinstance(prior_periods_raw, list):
            for prior in prior_periods_raw:
                if not isinstance(prior, dict):
                    continue
                try:
                    prior_starts.append(parse_date(prior.get("cycle_start_date")))
                except (TypeError, ValueError):
                    continue
        resolved = _priors_resolve_unusual_gap(existing_starts, start, prior_starts)
        already_acknowledged = (
            not start_changed
            and cycle.gap_reason in GAP_REASON_CHOICES
            and has_reason
        )

        if not has_reason:
            return _unusual_gap_response(
                gap_info, requires_prior_period=not bool(cycle.gap_reason)
            )
        if not already_acknowledged and not resolved:
            return _unusual_gap_response(gap_info, requires_prior_period=True)

    errors = _validate_cycle_payload(data, require_gap_fields=bool(gap_info and not gap_reason))
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        start = parse_date(data.get("cycle_start_date"))
        end = parse_date(data.get("cycle_end_date"))
        prior_periods = _parse_prior_periods(data)
        extra_starts = [p["cycle_start_date"] for p in prior_periods]
        predicted = _predict_next_period(
            current_user.id,
            start,
            extra_starts=extra_starts,
            exclude_id=cycle.id,
        )

        created = []
        for prior in prior_periods:
            exists = (
                CycleHistoryLog.query.filter_by(
                    profile_id=current_user.id,
                    cycle_start_date=prior["cycle_start_date"],
                ).first()
            )
            if exists:
                continue
            prior_predicted = _predict_next_period(
                current_user.id,
                prior["cycle_start_date"],
                extra_starts=extra_starts + [start],
                exclude_id=cycle.id,
            )
            prior_cycle = CycleHistoryLog(
                profile_id=current_user.id,
                cycle_start_date=prior["cycle_start_date"],
                cycle_end_date=prior["cycle_end_date"],
                flow_intensity=prior["flow_intensity"],
                notes=prior["notes"],
                gap_reason=prior["gap_reason"],
                predicted_next_period_date=prior_predicted,
            )
            db.session.add(prior_cycle)
            created.append(prior_cycle)

        cycle.cycle_start_date = start
        cycle.cycle_end_date = end
        cycle.flow_intensity = str(data.get("flow_intensity")).strip()
        cycle.notes = str(data.get("notes")).strip() if data.get("notes") else None
        if gap_reason:
            cycle.gap_reason = gap_reason
        cycle.predicted_next_period_date = predicted
        db.session.commit()

        return message_response(
            "cycle.updated_success",
            "Cycle entry updated successfully.",
            200,
            cycle=cycle.to_dict(),
            prior_cycles=[c.to_dict() for c in created],
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


def predict_conceive():
    from app.services.conceive_insights_service import compute_conceive_insights

    return jsonify(compute_conceive_insights(current_user)), 200
