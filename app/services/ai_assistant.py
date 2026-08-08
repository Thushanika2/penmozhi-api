import logging
import json
import re
from datetime import date, datetime, timedelta

from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.models.user_profile_model import UserProfile
from app.services.cycle_prediction_service import compute_cycle_insights

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 2048
# Keep Gemini thinking small so thoughts do not consume the output budget.
GEMINI_THINKING_BUDGET = 256
CONVERSATION_HISTORY_LIMIT = 10
MAX_CLARIFY_OPTIONS = 4

LANGUAGE_MATCHING_RULE = (
    "LANGUAGE MATCHING — CRITICAL: Detect the language of the user's most recent "
    "message. If they wrote in English, respond ENTIRELY in English. If they wrote "
    "in Tamil, respond entirely in Tamil. Never mix languages within one response, "
    "and never default to Tamil just because other parts of this system prompt, "
    "conversation history, user context, or reference material are in Tamil — only "
    "the user's own most recent message determines the response language. "
    "மொழிப் பொருத்தம் — மிக முக்கியம்: பயனரின் மிகச் சமீபத்திய செய்தி ஆங்கிலத்தில் "
    "இருந்தால் முழுவதும் ஆங்கிலத்தில் பதிலளிக்கவும்; தமிழில் இருந்தால் முழுவதும் "
    "தமிழில் பதிலளிக்கவும். மற்ற வழிமுறைகள் அல்லது குறிப்புத் தகவல்கள் தமிழில் "
    "இருப்பதால் தமிழை இயல்புநிலையாகத் தேர்ந்தெடுக்க வேண்டாம்."
)

SYSTEM_PROMPT = (
    f"{LANGUAGE_MATCHING_RULE} "
    "You are a knowledgeable, warm women's health expert for the Penmozhi app. "
    "Speak like a trusted specialist who knows this user personally. "
    "When internal user reference data is provided, weave relevant facts naturally "
    "into warm, conversational sentences — the way a real doctor would talk to a patient. "
    "The reference block is INTERNAL ONLY: NEVER quote, label, or repeat it verbatim. "
    "NEVER say phrases like 'according to your recorded data', '(User Context)', "
    "'பதிவு செய்யப்பட்ட தரவுகளின்படி', or repeat raw field labels like "
    "'Last period start date:' or 'Average cycle length:'. "
    "Instead say things like 'உங்க கடைசி பீரியட் ஜூலை மாசம் ஆரம்பிச்சிருக்கு, "
    "அதனால தற்போது நீங்க follicular phase-ல இருக்கலாம்'. "
    "Answer ONLY using facts from the internal reference data and the user's question. "
    "Never fabricate medical claims, lab results, or diagnoses. "
    "Always recommend consulting a qualified clinician for diagnosis or treatment. "
    "Keep every full answer concise: usually 3-5 short sentences. "
    "Cover only what the user asked — do not pack extra background, long hormone "
    "lectures, or unrelated tips into the same reply. "
    "Always finish with a complete sentence and clear ending punctuation; never stop mid-word. "
    "When prior conversation turns are provided, treat follow-up questions in context "
    "of what was already discussed — do not ask the user to repeat themselves. "
    "Never use markdown formatting (no **, no #, no bullet points with - or *). "
    "Write in plain conversational sentences only, since the output is displayed as plain text. "
    "If the reference data lacks information to answer, say so clearly. "
    "OUTPUT FORMAT: Always respond as JSON matching this schema only: "
    '{"response_type":"answer"|"clarify","text":"...","options":["..."]}. '
    "Use response_type \"answer\" for a normal reply; set text to the full answer and "
    "omit options or use an empty array. "
    "CLARIFYING QUESTIONS: Before giving a full answer, check whether you have enough "
    "information to give a genuinely useful, specific response. If the question is ambiguous, "
    "vague, or missing a detail that would meaningfully change your answer, ask ONE short, "
    "specific follow-up with response_type \"clarify\". Put the clarifying question in text. "
    "When the possible answers are enumerable (pain location, severity, yes/no-style "
    "distinctions, common causes), also provide 2-4 short mutually exclusive options "
    "(each under about 4 words) that the user can tap — e.g. text \"வலி எங்க வருது?\" "
    "with options [\"கீழ் வயிறு\", \"மேல் வயிறு\", \"இடுப்பு பகுதி\"]. "
    "If the clarifying detail cannot be reduced to short choices (e.g. exact days late), "
    "use response_type \"clarify\" with an empty options array so the user can type freely. "
    "Examples of when to ask a follow-up: "
    "'period late aachu' — clarify how many days late or whether anything unusual happened "
    "(stress, weight change, missed contraception, travel), not a generic late-period lecture; "
    "'vayitru vali irukku' — clarify location/severity with tappable options when possible; "
    "'enakku PCOS irukka' — clarify which symptoms they notice, not a generic PCOS list. "
    "Examples of when NOT to ask a follow-up (answer directly with response_type \"answer\"): "
    "the question is already specific and self-contained (e.g. 'average cycle length enna', "
    "'ovulation na enna'); the user already gave enough context in this message or earlier in "
    "the conversation; it is a general educational question with one clear factual answer. "
    "Rules for clarifying turns: ask only ONE clarifying question at a time; "
    "keep text short and conversational; never ask more than one clarifying round in a row — "
    "if your last reply was already a clarifying question and the user's next message still "
    "does not fully clarify, give your best answer with response_type \"answer\"; "
    "if the user seems distressed, in pain, or describes something urgent (heavy bleeding, "
    "severe pain, signs of a medical emergency), do NOT delay with a clarifying question — "
    "respond directly with response_type \"answer\" and recommend seeing a doctor or "
    "emergency care promptly."
)

_CONTEXT_PREAMBLE = (
    "LANGUAGE NOTE: The reference material below may be in Tamil or another language, "
    "but it must never determine the reply language. Respond only in the detected "
    "language of the user's own most recent message. "
    "INTERNAL REFERENCE DATA ABOUT THIS USER — for your eyes only. "
    "Use these facts to personalize your answer but NEVER quote, label, list, "
    "or repeat this block or its field names in your reply."
)

_CONTEXT_HEADER = "[INTERNAL USER REFERENCE — do not repeat in reply]"
_CONTEXT_FOOTER = "[END INTERNAL REFERENCE]"

_PHASE_LABELS = {
    "menstrual": "Menstrual",
    "follicular": "Follicular",
    "ovulation": "Ovulation",
    "fertile": "Ovulation (fertile window)",
    "luteal": "Luteal",
    "pms": "Luteal (PMS window)",
}


def detect_message_language(message: str | None) -> str:
    """Classify Tamil-script messages as Tamil; otherwise default to English."""
    text = message or ""
    return "Tamil" if re.search(r"[\u0B80-\u0BFF]", text) else "English"


def build_language_directive(message: str | None) -> str:
    language = detect_message_language(message)
    return (
        f"DETECTED USER MESSAGE LANGUAGE: {language}. "
        f"Your entire response text and all clarification options must be in {language}. "
        "Ignore the language of conversation history and reference data when choosing "
        "the response language."
    )


def build_system_instruction(user_context: str | None, message: str | None = None) -> str:
    """Persona, safety rules, and cycle context — kept out of turn-by-turn contents."""
    parts = [build_language_directive(message), SYSTEM_PROMPT]
    context = (user_context or "").strip()
    if context:
        parts.extend([
            "",
            _CONTEXT_PREAMBLE,
            _CONTEXT_HEADER,
            context,
            _CONTEXT_FOOTER,
        ])
    return "\n".join(parts)


def build_gemini_contents(
    history_messages: list[dict[str, str]],
    new_message: str,
) -> list[dict]:
    """Build alternating user/model turns for Gemini multi-turn chat."""
    contents: list[dict] = []
    for msg in history_messages:
        role = "user" if msg.get("role") == "user" else "model"
        text = (msg.get("content") or "").strip()
        if not text:
            continue
        contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": new_message}]})
    return contents


def format_llm_user_content(message: str, user_context: str | None) -> str:
    parts: list[str] = []
    context = (user_context or "").strip()
    if context:
        parts.extend([
            _CONTEXT_PREAMBLE,
            _CONTEXT_HEADER,
            context,
            _CONTEXT_FOOTER,
            "",
        ])
    parts.append(f"User message: {message}")
    return "\n".join(parts)


def sanitize_assistant_reply(text: str) -> str:
    """Strip markdown characters the UI cannot render."""
    if not text:
        return ""

    cleaned = text.replace("**", "").replace("__", "")

    lines: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.lstrip()
        while stripped.startswith("#"):
            stripped = stripped[1:].lstrip()
        if stripped.startswith(("- ", "* ", "• ")):
            stripped = stripped[2:].lstrip()
        lines.append(stripped)

    cleaned = "\n".join(lines)
    cleaned = cleaned.replace("*", "").replace("_", "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def normalize_assistant_payload(payload: dict | None, *, fallback_text: str | None = None) -> dict:
    """Normalize model output into {response_type, text, options}."""
    raw = payload if isinstance(payload, dict) else {}
    text = sanitize_assistant_reply(str(raw.get("text") or fallback_text or ""))
    response_type = str(raw.get("response_type") or "answer").strip().lower()
    if response_type not in {"answer", "clarify"}:
        response_type = "answer"

    options: list[str] = []
    raw_options = raw.get("options")
    if isinstance(raw_options, list) and response_type == "clarify":
        for item in raw_options:
            label = sanitize_assistant_reply(str(item or "").strip())
            if label and label not in options:
                options.append(label)
            if len(options) >= MAX_CLARIFY_OPTIONS:
                break

    if response_type == "clarify" and not text:
        response_type = "answer"

    return {
        "response_type": response_type,
        "text": text,
        "options": options if response_type == "clarify" else [],
    }


def parse_structured_assistant_response(raw_text: str | None) -> dict:
    """Parse Gemini JSON (or plain text fallback) into a normalized assistant payload."""
    if not raw_text or not str(raw_text).strip():
        return normalize_assistant_payload({"response_type": "answer", "text": ""})

    text = str(raw_text).strip()
    # Strip accidental markdown fences if the model ignores JSON mime mode.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return normalize_assistant_payload(parsed)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    return normalize_assistant_payload({"response_type": "answer", "text": text})


def gemini_response_schema(types):
    """Schema for Gemini JSON mode structured chat replies."""
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "response_type": types.Schema(
                type=types.Type.STRING,
                enum=["answer", "clarify"],
            ),
            "text": types.Schema(type=types.Type.STRING),
            "options": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                max_items=MAX_CLARIFY_OPTIONS,
            ),
        },
        required=["response_type", "text"],
    )


def _format_phase(phase: str | None) -> str | None:
    if not phase:
        return None
    return _PHASE_LABELS.get(phase, phase.replace("_", " ").title())


def _calculate_age(date_of_birth: date | None) -> int | None:
    if not date_of_birth:
        return None
    today = date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


def _format_symptom_summary(symptoms: list[SymptomTrackingLog]) -> str | None:
    if not symptoms:
        return None

    parts = []
    for symptom in symptoms[:3]:
        days_ago = (date.today() - symptom.date_time.date()).days
        label = symptom.category
        if symptom.pain_severity >= 4:
            label = f"{label} (pain {symptom.pain_severity}/10)"
        if symptom.mood_status:
            label = f"{label}, mood: {symptom.mood_status}"
        when = "today" if days_ago == 0 else f"{days_ago} days ago"
        parts.append(f"{label} ({when})")

    return "; ".join(parts)


def _latest_pcos_status(health: HealthProfile | None) -> PCOSDisorderStatus | None:
    if not health:
        return None
    return (
        PCOSDisorderStatus.query.filter_by(health_profile_id=health.id)
        .order_by(PCOSDisorderStatus.created_at.desc())
        .first()
    )


def _format_pcos_status(pcos: PCOSDisorderStatus | None) -> str | None:
    if not pcos:
        return None
    if pcos.diagnosis_status and pcos.diagnosis_status != "not_diagnosed":
        return f"{pcos.diagnosis_status.replace('_', ' ')} ({pcos.disorder_type})"
    if pcos.disorder_type and pcos.disorder_type != "none":
        return pcos.disorder_type.replace("_", " ")
    return None


def build_user_context(user_id: int) -> str:
    """
    Build a short plain-text summary of the user's health data for AI personalization.
    Returns an empty string if context building fails; never raises.
    """
    try:
        user = UserProfile.query.filter_by(id=user_id).first()
        if not user:
            return "No cycle data logged yet."

        health = HealthProfile.query.filter_by(profile_id=user_id).first()
        insights = compute_cycle_insights(user)

        lines: list[str] = []

        age = _calculate_age(user.date_of_birth)
        if age is not None:
            lines.append(f"Age: {age}")

        if insights.get("has_data"):
            avg_cycle = insights.get("average_cycle_length")
            avg_period = insights.get("average_period_length")
            if avg_cycle:
                lines.append(f"Average cycle length: {avg_cycle} days")
            if avg_period:
                lines.append(f"Average period length: {avg_period} days")

            last_start_raw = insights.get("last_period_start")
            if last_start_raw:
                last_start = date.fromisoformat(last_start_raw)
                days_since = (date.today() - last_start).days
                lines.append(f"Last period started: {days_since} days ago")

            phase_label = _format_phase(insights.get("current_phase"))
            if phase_label:
                lines.append(f"Estimated phase: {phase_label}")
        elif health:
            if health.average_cycle_length:
                lines.append(f"Average cycle length: {health.average_cycle_length} days")
            if health.average_period_length:
                lines.append(f"Average period length: {health.average_period_length} days")
            if health.last_period_start:
                days_since = (date.today() - health.last_period_start).days
                lines.append(f"Last period started: {days_since} days ago")

        cutoff = datetime.utcnow() - timedelta(days=7)
        recent_symptoms = (
            SymptomTrackingLog.query.filter_by(profile_id=user_id)
            .filter(SymptomTrackingLog.date_time >= cutoff)
            .order_by(SymptomTrackingLog.date_time.desc())
            .limit(5)
            .all()
        )
        symptom_summary = _format_symptom_summary(recent_symptoms)
        if symptom_summary:
            lines.append(f"Recent symptoms logged: {symptom_summary}")

        pcos_summary = _format_pcos_status(_latest_pcos_status(health))
        if pcos_summary:
            lines.append(f"PCOS status: {pcos_summary}")

        if not lines:
            return "No cycle data logged yet."

        return "\n".join(lines[:5])
    except Exception:
        logger.warning("Failed to build AI user context for profile_id=%s", user_id)
        return ""
