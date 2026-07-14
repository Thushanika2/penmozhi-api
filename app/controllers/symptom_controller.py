from collections import defaultdict

from flask import jsonify, request
from flask_jwt_extended import current_user

from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.utils import parse_datetime, utc_now


def _active_disorder_status_id(profile_id):
    health = HealthProfile.query.filter_by(profile_id=profile_id).first()
    if not health:
        return None
    status = (
        PCOSDisorderStatus.query.filter_by(health_profile_id=health.id)
        .order_by(PCOSDisorderStatus.created_at.desc())
        .first()
    )
    return status.id if status else None


def _validate_symptom_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    if data.get("category") is None or str(data.get("category")).strip() == "":
        errors.append("category is required.")

    if data.get("pain_severity") is None or str(data.get("pain_severity")).strip() == "":
        errors.append("pain_severity is required.")
    else:
        try:
            severity = int(data.get("pain_severity"))
            if severity < 0 or severity > 10:
                errors.append("pain_severity must be between 0 and 10.")
        except (TypeError, ValueError):
            errors.append("pain_severity must be an integer.")

    if data.get("date_time"):
        try:
            parse_datetime(data.get("date_time"))
        except ValueError:
            errors.append("date_time must be a valid ISO datetime.")

    return errors


def create_symptom():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    errors = _validate_symptom_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        disorder_status_id = data.get("disorder_status_id")
        if disorder_status_id is None:
            disorder_status_id = _active_disorder_status_id(current_user.id)
        elif disorder_status_id == "" or disorder_status_id is False:
            disorder_status_id = None
        else:
            disorder_status_id = int(disorder_status_id)

        symptom = SymptomTrackingLog(
            profile_id=current_user.id,
            date_time=parse_datetime(data.get("date_time")) or utc_now(),
            category=str(data.get("category")).strip(),
            pain_severity=int(data.get("pain_severity")),
            mood_status=(
                str(data.get("mood_status")).strip()
                if data.get("mood_status")
                else None
            ),
            sleep_metrics=(
                str(data.get("sleep_metrics")).strip()
                if data.get("sleep_metrics")
                else None
            ),
            disorder_status_id=disorder_status_id,
        )
        db.session.add(symptom)
        db.session.commit()

        response = {
            "message": "Symptom entry created successfully.",
            "symptom": symptom.to_dict(),
        }
        if symptom.pain_severity >= 7:
            response["ai_flag"] = (
                "High pain severity detected. Review your PCOS status and "
                "consider asking the AI Health Assistant for recommendations."
            )

        return jsonify(response), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "An internal server error occurred."}), 500


def get_my_symptoms():
    symptoms = (
        SymptomTrackingLog.query.filter_by(profile_id=current_user.id)
        .order_by(SymptomTrackingLog.date_time.desc())
        .all()
    )
    return jsonify({"symptoms": [s.to_dict() for s in symptoms]}), 200


def get_symptom_trends():
    symptoms = (
        SymptomTrackingLog.query.filter_by(profile_id=current_user.id)
        .order_by(SymptomTrackingLog.date_time.asc())
        .all()
    )

    by_date = defaultdict(lambda: {"count": 0, "avg_pain": 0.0, "pain_sum": 0})
    by_category = defaultdict(lambda: {"count": 0, "avg_pain": 0.0, "pain_sum": 0})

    for symptom in symptoms:
        day = symptom.date_time.date().isoformat() if symptom.date_time else "unknown"
        by_date[day]["count"] += 1
        by_date[day]["pain_sum"] += symptom.pain_severity

        cat = symptom.category or "uncategorized"
        by_category[cat]["count"] += 1
        by_category[cat]["pain_sum"] += symptom.pain_severity

    date_trends = []
    for day, stats in sorted(by_date.items()):
        date_trends.append({
            "date": day,
            "count": stats["count"],
            "avg_pain": round(stats["pain_sum"] / stats["count"], 2),
        })

    category_trends = []
    for cat, stats in sorted(by_category.items()):
        category_trends.append({
            "category": cat,
            "count": stats["count"],
            "avg_pain": round(stats["pain_sum"] / stats["count"], 2),
        })

    return jsonify({
        "date_trends": date_trends,
        "category_trends": category_trends,
        "total_entries": len(symptoms),
    }), 200
