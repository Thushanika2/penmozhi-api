import logging
import re
from datetime import date, datetime, timedelta

from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.models.user_profile_model import UserProfile
from app.services.cycle_prediction_service import compute_cycle_insights

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 1024
CONVERSATION_HISTORY_LIMIT = 10

SYSTEM_PROMPT = (
    "You are a knowledgeable, warm women's health expert for the Penmozhi app. "
    "Speak like a trusted specialist who knows this user personally. "
    "Reply in the same language the user writes in (English or Tamil). "
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
    "Keep every full answer to 3-5 short sentences maximum. "
    "When prior conversation turns are provided, treat follow-up questions in context "
    "of what was already discussed — do not ask the user to repeat themselves. "
    "Never use markdown formatting (no **, no #, no bullet points with - or *). "
    "Write in plain conversational sentences only, since the output is displayed as plain text. "
    "If the reference data lacks information to answer, say so clearly. "
    "CLARIFYING QUESTIONS: Before giving a full answer, check whether you have enough "
    "information to give a genuinely useful, specific response. If the question is ambiguous, "
    "vague, or missing a detail that would meaningfully change your answer, ask ONE short, "
    "specific follow-up question instead of answering generically. "
    "Examples of when to ask a follow-up: "
    "'period late aachu' — ask how many days late and whether anything unusual happened recently "
    "(stress, weight change, missed contraception, travel), not a generic list of late-period causes; "
    "'vayitru vali irukku' — ask where exactly, how severe, and whether it matches their usual cramps "
    "or feels different this time; "
    "'enakku PCOS irukka' — ask what symptoms they are noticing, not a generic PCOS symptom list. "
    "Examples of when NOT to ask a follow-up (answer directly): "
    "the question is already specific and self-contained (e.g. 'average cycle length enna', "
    "'ovulation na enna'); the user already gave enough context in this message or earlier in "
    "the conversation; it is a general educational question with one clear factual answer. "
    "Rules for the follow-up question itself: ask only ONE question at a time, not a list; "
    "keep it short and conversational, not clinical or interrogative; one or two sentences is enough; "
    "never ask more than one clarifying round in a row — if your last reply was already a "
    "clarifying question and the user's next message still does not fully clarify, give your "
    "best answer with the information available rather than asking again; "
    "if the user seems distressed, in pain, or describes something urgent (heavy bleeding, "
    "severe pain, signs of a medical emergency), do NOT delay with a clarifying question — "
    "respond directly and recommend seeing a doctor or emergency care promptly."
)

_CONTEXT_PREAMBLE = (
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


def build_system_instruction(user_context: str | None) -> str:
    """Persona, safety rules, and cycle context — kept out of turn-by-turn contents."""
    parts = [SYSTEM_PROMPT]
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
