import logging

from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, validation_errors
from app.extensions import db
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.services.ai_assistant import CONVERSATION_HISTORY_LIMIT, build_user_context
from app.services.ai_assistant_chat_store import (
    append_exchange,
    chat_list_item,
    create_session,
    ensure_ai_session_schema,
    get_recent_messages,
    get_session_for_user,
    list_sessions_for_user,
    parse_chat_messages,
    session_preview,
)
from app.services.pcos_pattern_service import detect_pcos_patterns
from app.services.ai_assistant_llm_service import (
    AssistantLLMUnavailable,
    generate_assistant_reply,
)

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


def _session_payload(session: AIHealthAssistantSession) -> dict:
    messages = parse_chat_messages(session.saved_chat_sessions)
    preview = session_preview(messages)
    return {
        **session.to_dict(),
        "messages": messages,
        "message_count": len(messages),
        "preview": preview,
    }


def chat():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    message = data.get("message")
    if message is None or str(message).strip() == "":
        return validation_errors([("validation.message_required", "message is required.")], 400)

    message = str(message).strip()
    chat_id = data.get("chat_id", data.get("session_id"))
    new_session = bool(data.get("new_session"))

    if chat_id is not None:
        try:
            chat_id = int(chat_id)
        except (TypeError, ValueError):
            return validation_errors(
                [("validation.session_id_invalid", "chat_id must be an integer.")],
                400,
            )

    try:
        # Ensure schema before session lookups (covers missing updated_at in prod).
        ensure_ai_session_schema()
        symptoms = (
            SymptomTrackingLog.query.filter_by(profile_id=current_user.id)
            .order_by(SymptomTrackingLog.date_time.desc())
            .limit(20)
            .all()
        )
        user_context = build_user_context(current_user.id)
        analysis = {
            "recent_symptom_count": len(symptoms),
            "max_pain": max((s.pain_severity for s in symptoms), default=0),
            "categories": list({s.category for s in symptoms}),
            "mode": current_user.mode,
        }

        existing = get_session_for_user(
            current_user.id,
            session_id=chat_id,
            new_session=new_session,
        )
        history_messages = (
            get_recent_messages(existing, CONVERSATION_HISTORY_LIMIT)
            if existing
            else []
        )

        try:
            payload = generate_assistant_reply(
                message,
                user_context,
                history_messages=history_messages,
            )
        except AssistantLLMUnavailable as exc:
            logger.error(
                "AI assistant LLM unavailable code=%s status=%s message=%s",
                exc.code,
                exc.status,
                exc.message,
            )
            # Never substitute rule-based recommendations into the chat reply.
            return error_response(exc.code, exc.message, exc.status)

        # Optional tips stored on the session only — never used as the chat reply.
        recommendations = _build_recommendations(message, symptoms)

        reply = payload["text"]
        response_type = payload.get("response_type") or "answer"
        options = payload.get("options") or []

        if existing:
            append_exchange(
                existing,
                message,
                reply,
                analysis=analysis,
                recommendations=recommendations,
                response_type=response_type,
                options=options,
            )
            session = existing
        else:
            session = create_session(
                current_user.id,
                message,
                reply,
                analysis=analysis,
                recommendations=recommendations,
                response_type=response_type,
                options=options,
            )

        db.session.commit()

        session_data = _session_payload(session)
        return jsonify({
            "message": "Chat response generated.",
            "message_code": "ai.chat_generated",
            "reply": reply,
            "response_type": response_type,
            "options": options if response_type == "clarify" else [],
            "recommendations": recommendations,
            "chat_id": session.id,
            "session_id": session.id,
            "messages": session_data["messages"],
            "session": session_data,
        }), 201
    except Exception:
        db.session.rollback()
        logger.exception("AI assistant chat failed.")
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_chat_history():
    session_id = request.args.get("session_id", type=int)

    try:
        ensure_ai_session_schema()
        if session_id is not None:
            session = get_session_for_user(current_user.id, session_id=session_id)
            if not session:
                return error_response("ai.session_not_found", "Chat session not found.", 404)
        else:
            session = get_session_for_user(current_user.id)

        if not session:
            return jsonify({
                "session_id": None,
                "messages": [],
                "session": None,
            }), 200

        session_data = _session_payload(session)
        return jsonify({
            "session_id": session.id,
            "messages": session_data["messages"],
            "session": session_data,
        }), 200
    except Exception:
        logger.exception("Failed to load AI assistant chat history.")
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
        ensure_ai_session_schema()
        sessions = list_sessions_for_user(current_user.id, limit=20)
        return jsonify({
            "sessions": [_session_payload(session) for session in sessions],
        }), 200
    except Exception:
        logger.exception("Failed to load AI assistant sessions.")
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_chats():
    """List past chats for the sidebar: chat_id, title, last_message_at."""
    try:
        ensure_ai_session_schema()
        sessions = list_sessions_for_user(current_user.id, limit=30)
        return jsonify({
            "chats": [chat_list_item(session) for session in sessions],
        }), 200
    except Exception:
        logger.exception("Failed to load AI assistant chats.")
        return error_response("server.internal_error", "An internal server error occurred.", 500)
