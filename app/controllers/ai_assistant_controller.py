import json
import logging

from flask import current_app, jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, validation_errors
from app.extensions import db
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.services.pcos_pattern_service import detect_pcos_patterns
from app.services.ai_assistant_llm_service import generate_assistant_reply

logger = logging.getLogger(__name__)


def _build_recommendations(message, symptoms):
    recommendations = []
    lower = (message or "").lower()

    high_pain = [s for s in symptoms if s.pain_severity >= 7]
    if high_pain or any(word in lower for word in ("pain", "cramp", "severe")):
        recommendations.append(
            "High pain patterns detected. Review your PCOS disorder status and "
            "consider consulting a clinician if pain persists."
        )

    if any(word in lower for word in ("pcos", "irregular", "cycle")):
        recommendations.append(
            "Track at least two full cycles so next-period prediction can update, "
            "and keep your PCOS status current under Dashboard → PCOS Status."
        )

    if any(word in lower for word in ("sleep", "insomnia", "tired")):
        recommendations.append(
            "Log sleep metrics with your symptoms to spot trends over time."
        )

    if any(word in lower for word in ("mood", "anxiety", "stress")):
        recommendations.append(
            "Mood changes can accompany hormonal shifts — keep daily mood logs "
            "and browse related educational resources."
        )

    if not recommendations:
        recommendations.append(
            "Continue logging cycles and symptoms regularly. Browse educational "
            "resources for evidence-based guidance on menstrual health."
        )

    return recommendations


def _active_pcos_status(user):
    health = HealthProfile.query.filter_by(profile_id=user.id).first()
    if not health:
        return None
    return (
        PCOSDisorderStatus.query.filter_by(health_profile_id=health.id)
        .order_by(PCOSDisorderStatus.created_at.desc())
        .first()
    )


def _build_llm_context(user):
    symptoms = (
        SymptomTrackingLog.query.filter_by(profile_id=user.id)
        .order_by(SymptomTrackingLog.date_time.desc())
        .limit(20)
        .all()
    )
    cycles = (
        CycleHistoryLog.query.filter_by(profile_id=user.id)
        .order_by(CycleHistoryLog.cycle_start_date.desc())
        .limit(6)
        .all()
    )
    pcos = _active_pcos_status(user)
    patterns = detect_pcos_patterns(user)

    return {
        "mode": user.mode,
        "recent_symptoms": [s.to_dict() for s in symptoms],
        "recent_cycles": [c.to_dict() for c in cycles],
        "pcos_status": pcos.to_dict() if pcos else None,
        "pcos_patterns": patterns.get("patterns", []),
    }


def chat():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    message = data.get("message")
    if message is None or str(message).strip() == "":
        return validation_errors([("validation.message_required", "message is required.")], 400)

    message = str(message).strip()

    try:
        symptoms = (
            SymptomTrackingLog.query.filter_by(profile_id=current_user.id)
            .order_by(SymptomTrackingLog.date_time.desc())
            .limit(20)
            .all()
        )
        context = _build_llm_context(current_user)
        analysis = {
            "recent_symptom_count": len(symptoms),
            "max_pain": max((s.pain_severity for s in symptoms), default=0),
            "categories": list({s.category for s in symptoms}),
            "mode": current_user.mode,
        }

        llm_reply = generate_assistant_reply(message, context)
        if llm_reply:
            reply = llm_reply
            recommendations = [llm_reply]
        else:
            recommendations = _build_recommendations(message, symptoms)
            reply = " ".join(recommendations)

        session = AIHealthAssistantSession(
            profile_id=current_user.id,
            symptom_analysis_log=json.dumps(analysis),
            generated_recommendations=json.dumps(recommendations),
            posted_messages=json.dumps([{"role": "user", "content": message}]),
            saved_chat_sessions=json.dumps([
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]),
        )
        db.session.add(session)
        db.session.commit()

        return jsonify({
            "message": "Chat response generated.",
            "message_code": "ai.chat_generated",
            "reply": reply,
            "recommendations": recommendations,
            "session": session.to_dict(),
        }), 201
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_recommendations():
    try:
        symptoms = (
            SymptomTrackingLog.query.filter_by(profile_id=current_user.id)
            .order_by(SymptomTrackingLog.date_time.desc())
            .limit(20)
            .all()
        )
        recommendations = _build_recommendations("", symptoms)

        patterns = detect_pcos_patterns(current_user).get("patterns", [])
        for pattern in patterns[:2]:
            description = pattern.get("description")
            if description and description not in recommendations:
                recommendations.append(description)

        return jsonify({"recommendations": recommendations}), 200
    except Exception:
        logger.exception("Failed to load AI assistant recommendations.")
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_sessions():
    try:
        sessions = (
            AIHealthAssistantSession.query.filter_by(profile_id=current_user.id)
            .order_by(AIHealthAssistantSession.created_at.desc())
            .limit(20)
            .all()
        )
        return jsonify({"sessions": [session.to_dict() for session in sessions]}), 200
    except Exception:
        logger.exception("Failed to load AI assistant sessions.")
        return error_response("server.internal_error", "An internal server error occurred.", 500)
