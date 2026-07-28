import json

from flask import jsonify, make_response
from flask_jwt_extended import current_user

from app.api_responses import error_response
from app.extensions import db
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.custom_tag_model import CustomTag
from app.models.daily_log_model import DailyLog
from app.models.health_profile_model import HealthProfile
from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.models.perimenopause_log_model import PerimenopauseLog
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.pregnancy_profile_model import PregnancyProfile
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.services.privacy_service import create_privacy_request


def export_account_data():
    user = current_user
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    try:
        create_privacy_request(user, "export")
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)

    health = HealthProfile.query.filter_by(profile_id=user.id).first()
    pcos_statuses = []
    if health:
        pcos_statuses = [s.to_dict() for s in health.pcos_disorder_statuses or []]

    export_payload = {
        "user": user.to_dict(),
        "health_profile": health.to_dict() if health else None,
        "pcos_statuses": pcos_statuses,
        "cycle_history_logs": [
            c.to_dict()
            for c in CycleHistoryLog.query.filter_by(profile_id=user.id).all()
        ],
        "symptom_tracking_logs": [
            s.to_dict()
            for s in SymptomTrackingLog.query.filter_by(profile_id=user.id).all()
        ],
        "daily_logs": [
            d.to_dict() for d in DailyLog.query.filter_by(profile_id=user.id).all()
        ],
        "medication_reminders": [
            r.to_dict()
            for r in MedicationSupplementReminder.query.filter_by(profile_id=user.id).all()
        ],
        "custom_tags": [
            t.to_dict() for t in CustomTag.query.filter_by(profile_id=user.id).all()
        ],
        "perimenopause_logs": [
            p.to_dict() for p in PerimenopauseLog.query.filter_by(profile_id=user.id).all()
        ],
        "pregnancy_profile": None,
        "ai_sessions": [
            s.to_dict()
            for s in AIHealthAssistantSession.query.filter_by(profile_id=user.id).all()
        ],
    }

    pregnancy = PregnancyProfile.query.filter_by(profile_id=user.id).first()
    if pregnancy:
        export_payload["pregnancy_profile"] = pregnancy.to_dict()

    response = make_response(json.dumps(export_payload, indent=2))
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Disposition"] = 'attachment; filename="penmozhi-export.json"'
    return response
