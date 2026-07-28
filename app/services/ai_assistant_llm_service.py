import logging

from flask import current_app

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a knowledgeable, warm women's health expert for the Penmozhi app. "
    "Speak like a trusted specialist who knows this user personally: when user context "
    "is provided, reference their own cycle length, last period, phase, symptoms, and "
    "PCOS status naturally (for example, 'your 28-day cycle' or 'உங்க cycle 28 நாள்') "
    "instead of only generic textbook advice. "
    "Answer ONLY using the user context provided in the message. "
    "Never fabricate medical claims, lab results, or diagnoses. "
    "Always recommend consulting a qualified clinician for diagnosis or treatment. "
    "Be supportive, concise, and evidence-aware. "
    "If the context lacks information to answer, say so clearly."
)

_USER_CONTEXT_HEADER = (
    "[USER CONTEXT — use this to personalize your answer, but never invent "
    "details not listed here]"
)
_USER_CONTEXT_FOOTER = "[END USER CONTEXT]"


def _format_user_content(message: str, user_context: str | None) -> str:
    parts: list[str] = []
    context = (user_context or "").strip()
    if context:
        parts.extend([_USER_CONTEXT_HEADER, context, _USER_CONTEXT_FOOTER, ""])
    parts.append(f"User message: {message}")
    return "\n".join(parts)


def _call_gemini(message: str, user_context: str | None) -> str | None:
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=current_app.config.get("GEMINI_MODEL", "gemini-flash-latest"),
            contents=_format_user_content(message, user_context),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=800,
                temperature=0.4,
            ),
        )
        text = (response.text or "").strip()
        return text or None
    except ImportError:
        logger.error(
            "google-genai is not installed. Run: pip install -r requirements.txt"
        )
        return None
    except Exception:
        logger.exception("Gemini call failed.")
        return None


def _call_anthropic(message: str, user_context: str | None) -> str | None:
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=current_app.config.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _format_user_content(message, user_context)},
            ],
        )
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]
        text = "\n".join(text_blocks).strip()
        return text or None
    except Exception:
        logger.exception("Anthropic call failed.")
        return None


def _provider_order() -> list[str]:
    provider = (current_app.config.get("AI_PROVIDER") or "auto").strip().lower()
    has_gemini = bool(current_app.config.get("GEMINI_API_KEY"))
    has_anthropic = bool(current_app.config.get("ANTHROPIC_API_KEY"))

    if provider == "gemini":
        return ["gemini"]
    if provider == "anthropic":
        return ["anthropic"]
    if provider == "auto":
        order = []
        if has_gemini:
            order.append("gemini")
        if has_anthropic:
            order.append("anthropic")
        return order

    logger.warning("Unknown AI_PROVIDER '%s'; using auto detection.", provider)
    order = []
    if has_gemini:
        order.append("gemini")
    if has_anthropic:
        order.append("anthropic")
    return order


def generate_assistant_reply(message: str, user_context: str | None = None) -> str | None:
    callers = {
        "gemini": _call_gemini,
        "anthropic": _call_anthropic,
    }

    for provider in _provider_order():
        reply = callers[provider](message, user_context)
        if reply:
            logger.info("AI assistant reply generated via %s.", provider)
            return reply

    return None
