import logging

from flask import current_app

from app.services.ai_assistant import (
    CONVERSATION_HISTORY_LIMIT,
    GEMINI_THINKING_BUDGET,
    MAX_OUTPUT_TOKENS,
    build_gemini_contents,
    build_system_instruction,
    sanitize_assistant_reply,
)

logger = logging.getLogger(__name__)


def _finish_reason_name(finish_reason) -> str:
    if finish_reason is None:
        return "UNKNOWN"
    return str(getattr(finish_reason, "name", None) or finish_reason)


def _extract_candidate_text(response) -> str:
    """Prefer response.text, fall back to concatenating text parts."""
    try:
        text = response.text
        if text:
            return text
    except Exception:
        # google-genai can raise when a truncated candidate has no easy .text
        pass

    chunks: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                chunks.append(part_text)
    return "\n".join(chunks).strip()


def _log_gemini_finish_reason(response) -> str:
    if not response.candidates:
        logger.warning("Gemini response has no candidates.")
        return "NO_CANDIDATES"

    candidate = response.candidates[0]
    finish_reason = candidate.finish_reason
    reason_name = _finish_reason_name(finish_reason)
    usage = getattr(response, "usage_metadata", None)
    thoughts = getattr(usage, "thoughts_token_count", None) if usage else None
    output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
    prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
    total_tokens = getattr(usage, "total_token_count", None) if usage else None

    logger.info(
        "Gemini finish_reason=%s prompt_tokens=%s thoughts_tokens=%s "
        "output_tokens=%s total_tokens=%s max_output_tokens=%s",
        reason_name,
        prompt_tokens,
        thoughts,
        output_tokens,
        total_tokens,
        MAX_OUTPUT_TOKENS,
    )

    if reason_name == "MAX_TOKENS":
        logger.warning(
            "Gemini response truncated (MAX_TOKENS). "
            "Thoughts often share the max_output_tokens budget on thinking models."
        )
    elif reason_name == "SAFETY":
        safety = getattr(candidate, "safety_ratings", None)
        logger.warning("Gemini response blocked/truncated by SAFETY. ratings=%s", safety)
    elif reason_name not in {"STOP", "FINISH_REASON_UNSPECIFIED", "UNKNOWN"}:
        logger.warning("Gemini unusual finish_reason=%s", reason_name)

    return reason_name


def _build_thinking_config(types):
    """
    Prefer a minimal thinking level so thoughts do not eat the output budget.
    Fall back to a small thinking_budget for models that do not support levels.
    """
    thinking_level = getattr(types, "ThinkingLevel", None)
    if thinking_level is not None and hasattr(thinking_level, "MINIMAL"):
        return types.ThinkingConfig(thinking_level=thinking_level.MINIMAL)
    return types.ThinkingConfig(thinking_budget=GEMINI_THINKING_BUDGET)


def _finalize_reply(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = sanitize_assistant_reply(text)
    return cleaned or None


def _to_gemini_content(raw_contents: list[dict]):
    from google.genai import types

    contents = []
    for entry in raw_contents:
        parts = [types.Part(text=part["text"]) for part in entry.get("parts", []) if part.get("text")]
        if parts:
            contents.append(types.Content(role=entry["role"], parts=parts))
    return contents


def _generate_with_gemini(client, model: str, contents, system_instruction: str, *, use_thinking: bool):
    from google.genai import types

    config_kwargs = {
        "system_instruction": system_instruction,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.4,
    }
    if use_thinking:
        config_kwargs["thinking_config"] = _build_thinking_config(types)

    return client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )


def _call_gemini(
    message: str,
    user_context: str | None,
    history_messages: list[dict[str, str]] | None = None,
) -> str | None:
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai.errors import ClientError

        # 60s gives thinking models room without leaving the client hanging forever.
        client = genai.Client(api_key=api_key, http_options={"timeout": 60_000})
        model = current_app.config.get("GEMINI_MODEL", "gemini-flash-latest")
        raw_contents = build_gemini_contents(history_messages or [], message)
        contents = _to_gemini_content(raw_contents)
        system_instruction = build_system_instruction(user_context)

        try:
            response = _generate_with_gemini(
                client,
                model,
                contents,
                system_instruction,
                use_thinking=True,
            )
        except ClientError as exc:
            # Some models reject thinking_level / thinking_budget values.
            logger.warning(
                "Gemini rejected thinking_config (%s); retrying without it.",
                exc,
            )
            response = _generate_with_gemini(
                client,
                model,
                contents,
                system_instruction,
                use_thinking=False,
            )

        reason_name = _log_gemini_finish_reason(response)
        reply = _finalize_reply(_extract_candidate_text(response))

        # If thinking still consumed the shared token budget, retry once with more headroom.
        if reason_name == "MAX_TOKENS":
            logger.warning(
                "Retrying Gemini once after MAX_TOKENS with max_output_tokens=%s.",
                MAX_OUTPUT_TOKENS * 2,
            )
            from google.genai import types

            retry_kwargs = {
                "system_instruction": system_instruction,
                "max_output_tokens": MAX_OUTPUT_TOKENS * 2,
                "temperature": 0.4,
            }
            try:
                retry_kwargs["thinking_config"] = _build_thinking_config(types)
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(**retry_kwargs),
                )
            except ClientError:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        max_output_tokens=MAX_OUTPUT_TOKENS * 2,
                        temperature=0.4,
                    ),
                )
            reason_name = _log_gemini_finish_reason(response)
            retry_reply = _finalize_reply(_extract_candidate_text(response))
            if retry_reply:
                reply = retry_reply
            if reason_name == "MAX_TOKENS":
                logger.error(
                    "Gemini reply still truncated after retry (finish_reason=MAX_TOKENS)."
                )

        return reply
    except ImportError:
        logger.error(
            "google-genai is not installed. Run: pip install -r requirements.txt"
        )
        return None
    except Exception:
        logger.exception("Gemini call failed.")
        return None


def _call_anthropic(
    message: str,
    user_context: str | None,
    history_messages: list[dict[str, str]] | None = None,
) -> str | None:
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
        messages = []
        for msg in history_messages or []:
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        response = client.messages.create(
            model=current_app.config.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
            max_tokens=MAX_OUTPUT_TOKENS,
            system=build_system_instruction(user_context),
            messages=messages,
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


def generate_assistant_reply(
    message: str,
    user_context: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
) -> str | None:
    callers = {
        "gemini": _call_gemini,
        "anthropic": _call_anthropic,
    }

    for provider in _provider_order():
        reply = callers[provider](message, user_context, history_messages)
        if reply:
            logger.info(
                "AI assistant reply generated via %s (%s prior turns, history_limit=%s).",
                provider,
                len(history_messages or []),
                CONVERSATION_HISTORY_LIMIT,
            )
            return reply

    return None
