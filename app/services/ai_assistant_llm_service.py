import json
import logging

from flask import current_app

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a women's health assistant for the Penmozhi app. "
    "Answer ONLY using the structured user context provided. "
    "Never fabricate medical claims, lab results, or diagnoses. "
    "Always recommend consulting a qualified clinician for diagnosis or treatment. "
    "Be supportive, concise, and evidence-aware. "
    "If the context lacks information to answer, say so clearly."
)


def _format_user_content(message: str, context: dict) -> str:
    return (
        f"User message: {message}\n\n"
        f"Context JSON:\n{json.dumps(context, indent=2, default=str)}"
    )


def _call_gemini(message: str, context: dict) -> str | None:
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash"),
            contents=_format_user_content(message, context),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=800,
                temperature=0.4,
            ),
        )
        text = (response.text or "").strip()
        return text or None
    except Exception:
        logger.exception("Gemini call failed.")
        return None


def _call_anthropic(message: str, context: dict) -> str | None:
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
                {"role": "user", "content": _format_user_content(message, context)},
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


def generate_assistant_reply(message: str, context: dict) -> str | None:
    callers = {
        "gemini": _call_gemini,
        "anthropic": _call_anthropic,
    }

    for provider in _provider_order():
        reply = callers[provider](message, context)
        if reply:
            logger.info("AI assistant reply generated via %s.", provider)
            return reply

    return None
