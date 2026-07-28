import json
from typing import Any

from app.extensions import db
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession


def parse_chat_messages(raw: str | None) -> list[dict[str, str]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(data, list):
        return []

    messages: list[dict[str, str]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role in ("user", "assistant") and content is not None:
            messages.append({"role": role, "content": str(content)})
    return messages


def session_preview(messages: list[dict[str, str]]) -> str | None:
    for entry in messages:
        if entry.get("role") == "user":
            text = (entry.get("content") or "").strip()
            if text:
                return text
    return None


def get_session_for_user(
    profile_id: int,
    session_id: int | None = None,
    *,
    new_session: bool = False,
) -> AIHealthAssistantSession | None:
    if new_session:
        return None

    query = AIHealthAssistantSession.query.filter_by(profile_id=profile_id)
    if session_id is not None:
        return query.filter_by(id=session_id).first()

    return query.order_by(AIHealthAssistantSession.created_at.desc()).first()


def append_exchange(
    session: AIHealthAssistantSession,
    user_message: str,
    assistant_reply: str,
    *,
    analysis: dict[str, Any] | None = None,
    recommendations: list[str] | None = None,
) -> list[dict[str, str]]:
    messages = parse_chat_messages(session.saved_chat_sessions)
    messages.extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_reply},
    ])
    session.saved_chat_sessions = json.dumps(messages)
    session.posted_messages = json.dumps(
        [entry for entry in messages if entry["role"] == "user"]
    )
    if analysis is not None:
        session.symptom_analysis_log = json.dumps(analysis)
    if recommendations is not None:
        session.generated_recommendations = json.dumps(recommendations)
    return messages


def create_session(
    profile_id: int,
    user_message: str,
    assistant_reply: str,
    *,
    analysis: dict[str, Any],
    recommendations: list[str],
) -> AIHealthAssistantSession:
    messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_reply},
    ]
    session = AIHealthAssistantSession(
        profile_id=profile_id,
        symptom_analysis_log=json.dumps(analysis),
        generated_recommendations=json.dumps(recommendations),
        posted_messages=json.dumps([{"role": "user", "content": user_message}]),
        saved_chat_sessions=json.dumps(messages),
    )
    db.session.add(session)
    return session
