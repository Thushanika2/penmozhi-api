import json

from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, validation_errors
from app.extensions import db
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession
from app.models.symptom_tracking_log_model import SymptomTrackingLog


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
        analysis = {
            "recent_symptom_count": len(symptoms),
            "max_pain": max((s.pain_severity for s in symptoms), default=0),
            "categories": list({s.category for s in symptoms}),
        }
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
    sessions = (
        AIHealthAssistantSession.query.filter_by(profile_id=current_user.id)
        .order_by(AIHealthAssistantSession.created_at.desc())
        .all()
    )
    recommendations = []
    for session in sessions:
        if not session.generated_recommendations:
            continue
        try:
            items = json.loads(session.generated_recommendations)
            if isinstance(items, list):
                recommendations.extend(items)
            else:
                recommendations.append(str(items))
        except json.JSONDecodeError:
            recommendations.append(session.generated_recommendations)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for item in recommendations:
        if item not in seen:
            seen.add(item)
            unique.append(item)

    return jsonify({"recommendations": unique}), 200


def get_sessions():
    sessions = (
        AIHealthAssistantSession.query.filter_by(profile_id=current_user.id)
        .order_by(AIHealthAssistantSession.created_at.desc())
        .all()
    )
    return jsonify({"sessions": [s.to_dict() for s in sessions]}), 200
