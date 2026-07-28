import logging

from flask import current_app

from app.services.ai_assistant import (
    MAX_OUTPUT_TOKENS,
    SYSTEM_PROMPT,
    format_llm_user_content,
    sanitize_assistant_reply,
)

logger = logging.getLogger(__name__)


def _log_gemini_finish_reason(response) -> None:
    if not response.candidates:
        logger.warning("Gemini response has no candidates.")
        return

    finish_reason = response.candidates[0].finish_reason
    logger.info("Gemini finish_reason: %s", finish_reason)

    reason_name = getattr(finish_reason, "name", str(finish_reason))
    if reason_name == "MAX_TOKENS":
        logger.warning(
            "Gemini response truncated (MAX_TOKENS). "
            "Consider shortening the reply prompt or raising max_output_tokens."
        )


def _finalize_reply(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = sanitize_assistant_reply(text)
    return cleaned or None


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
            contents=format_llm_user_content(message, user_context),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.4,
            ),
        )
        _log_gemini_finish_reason(response)
        return _finalize_reply(response.text)
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
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": format_llm_user_content(message, user_context)},
            ],
        )
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]
        return _finalize_reply("\n".join(text_blocks).strip())
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
