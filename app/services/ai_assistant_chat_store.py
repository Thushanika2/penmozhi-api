import json
from typing import Any

from app.utils import utc_now
from app.extensions import db
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession


def parse_chat_messages(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(data, list):
        return []

    messages: list[dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role not in ("user", "assistant") or content is None:
            continue

        message: dict[str, Any] = {
            "role": role,
            "content": str(content),
        }
        if role == "assistant":
            response_type = str(entry.get("response_type") or "answer").strip().lower()
            if response_type not in {"answer", "clarify"}:
                response_type = "answer"
            message["response_type"] = response_type
            options = entry.get("options")
            if response_type == "clarify" and isinstance(options, list):
                cleaned = []
                for item in options:
                    label = str(item or "").strip()
                    if label and label not in cleaned:
                        cleaned.append(label)
                    if len(cleaned) >= 4:
                        break
                message["options"] = cleaned
            else:
                message["options"] = []
        messages.append(message)
    return messages


def history_for_llm(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Strip UI metadata before sending turns back to the model."""
    return [
        {"role": entry["role"], "content": entry["content"]}
        for entry in messages
        if entry.get("role") in {"user", "assistant"} and entry.get("content") is not None
    ]


def session_preview(messages: list[dict[str, Any]], *, max_len: int = 40) -> str | None:
    for entry in messages:
        if entry.get("role") == "user":
            text = (entry.get("content") or "").strip()
            if text:
                if len(text) <= max_len:
                    return text
                return text[: max_len - 1].rstrip() + "…"
    return None


def chat_list_item(session: AIHealthAssistantSession) -> dict[str, Any]:
    messages = parse_chat_messages(session.saved_chat_sessions)
    title = session_preview(messages) or "Chat"
    last_at = session.updated_at or session.created_at
    return {
        "chat_id": session.id,
        "title": title,
        "last_message_at": last_at.isoformat() if last_at else None,
        "message_count": len(messages),
    }


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

    return query.order_by(
        AIHealthAssistantSession.updated_at.desc(),
        AIHealthAssistantSession.created_at.desc(),
    ).first()


def get_recent_messages(
    session: AIHealthAssistantSession,
    limit: int = 10,
) -> list[dict[str, str]]:
    """Return the last N stored messages for a session, oldest first (LLM-ready)."""
    messages = parse_chat_messages(session.saved_chat_sessions)
    if len(messages) > limit:
        messages = messages[-limit:]
    return history_for_llm(messages)


def _assistant_message(
    assistant_reply: str,
    *,
    response_type: str = "answer",
    options: list[str] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": assistant_reply,
        "response_type": response_type if response_type in {"answer", "clarify"} else "answer",
        "options": [],
    }
    if message["response_type"] == "clarify" and options:
        cleaned = []
        for item in options:
            label = str(item or "").strip()
            if label and label not in cleaned:
                cleaned.append(label)
            if len(cleaned) >= 4:
                break
        message["options"] = cleaned
    return message


def append_exchange(
    session: AIHealthAssistantSession,
    user_message: str,
    assistant_reply: str,
    *,
    analysis: dict[str, Any] | None = None,
    recommendations: list[str] | None = None,
    response_type: str = "answer",
    options: list[str] | None = None,
) -> list[dict[str, Any]]:
    messages = parse_chat_messages(session.saved_chat_sessions)
    messages.extend([
        {"role": "user", "content": user_message},
        _assistant_message(
            assistant_reply,
            response_type=response_type,
            options=options,
        ),
    ])
    session.saved_chat_sessions = json.dumps(messages)
    session.posted_messages = json.dumps(
        [{"role": "user", "content": entry["content"]} for entry in messages if entry["role"] == "user"]
    )
    if analysis is not None:
        session.symptom_analysis_log = json.dumps(analysis)
    if recommendations is not None:
        session.generated_recommendations = json.dumps(recommendations)
    session.updated_at = utc_now()
    return messages


def create_session(
    profile_id: int,
    user_message: str,
    assistant_reply: str,
    *,
    analysis: dict[str, Any],
    recommendations: list[str],
    response_type: str = "answer",
    options: list[str] | None = None,
) -> AIHealthAssistantSession:
    messages = [
        {"role": "user", "content": user_message},
        _assistant_message(
            assistant_reply,
            response_type=response_type,
            options=options,
        ),
    ]
    now = utc_now()
    session = AIHealthAssistantSession(
        profile_id=profile_id,
        symptom_analysis_log=json.dumps(analysis),
        generated_recommendations=json.dumps(recommendations),
        posted_messages=json.dumps([{"role": "user", "content": user_message}]),
        saved_chat_sessions=json.dumps(messages),
        created_at=now,
        updated_at=now,
    )
    db.session.add(session)
    return session
