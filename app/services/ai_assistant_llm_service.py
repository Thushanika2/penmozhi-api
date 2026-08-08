import logging
from dataclasses import dataclass

from flask import current_app

from app.services.ai_assistant import (
    CONVERSATION_HISTORY_LIMIT,
    GEMINI_THINKING_BUDGET,
    MAX_OUTPUT_TOKENS,
    build_gemini_contents,
    build_system_instruction,
    gemini_response_schema,
    normalize_assistant_payload,
    parse_structured_assistant_response,
    sanitize_assistant_reply,
)

logger = logging.getLogger(__name__)

# Prefer flash-lite aliases — full flash free-tier caps are often exhausted first.
DEFAULT_GEMINI_FALLBACK_MODELS = (
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.0-flash",
)


class AssistantLLMUnavailable(Exception):
    """Raised when no LLM provider can produce a chat reply."""

    def __init__(self, code: str, message: str, status: int = 503):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass
class _GeminiAttempt:
    model: str
    status_code: int | None = None
    raw_body: str | None = None
    exception_caught: bool = False
    exception_type: str | None = None
    finish_reason: str | None = None
    raw_text: str | None = None
    payload: dict | None = None


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


def _finalize_payload_from_raw(raw_text: str | None) -> dict | None:
    payload = parse_structured_assistant_response(raw_text)
    if not payload.get("text"):
        return None
    return payload


def _to_gemini_content(raw_contents: list[dict]):
    from google.genai import types

    contents = []
    for entry in raw_contents:
        parts = [types.Part(text=part["text"]) for part in entry.get("parts", []) if part.get("text")]
        if parts:
            contents.append(types.Content(role=entry["role"], parts=parts))
    return contents


def _client_error_details(exc) -> tuple[int | None, str]:
    status = getattr(exc, "code", None)
    if not isinstance(status, int):
        status = getattr(exc, "status_code", None)
    body = getattr(exc, "details", None)
    if body is None:
        body = getattr(exc, "message", None) or str(exc)
    if not isinstance(body, str):
        try:
            import json

            body = json.dumps(body, default=str)
        except Exception:
            body = str(body)
    return status if isinstance(status, int) else None, body


def _is_quota_error(exc) -> bool:
    status, body = _client_error_details(exc)
    text = (body or "").upper()
    return status == 429 or "RESOURCE_EXHAUSTED" in text or "QUOTA" in text


def _is_thinking_config_error(exc) -> bool:
    """True when the model rejected thinking_config (not quota/auth failures)."""
    if _is_quota_error(exc):
        return False
    status, body = _client_error_details(exc)
    text = (body or "").lower()
    if status in {401, 403, 404}:
        return False
    return any(
        token in text
        for token in (
            "thinking",
            "thinking_config",
            "thinking_budget",
            "thinking_level",
            "invalid argument",
            "unsupported",
        )
    )


def _log_gemini_attempt(attempt: _GeminiAttempt) -> None:
    logger.info(
        "GEMINI_DIAGNOSTIC model=%s http_status=%s exception_caught=%s "
        "exception_type=%s finish_reason=%s raw_body=%s raw_text=%s payload=%s",
        attempt.model,
        attempt.status_code,
        attempt.exception_caught,
        attempt.exception_type,
        attempt.finish_reason,
        (attempt.raw_body or "")[:4000],
        (attempt.raw_text or "")[:2000],
        attempt.payload,
    )


def _generate_with_gemini(
    client,
    model: str,
    contents,
    system_instruction: str,
    *,
    use_thinking: bool,
    max_output_tokens: int | None = None,
):
    from google.genai import types

    config_kwargs = {
        "system_instruction": system_instruction,
        "max_output_tokens": max_output_tokens or MAX_OUTPUT_TOKENS,
        "temperature": 0.4,
        "response_mime_type": "application/json",
        "response_schema": gemini_response_schema(types),
    }
    if use_thinking:
        config_kwargs["thinking_config"] = _build_thinking_config(types)

    return client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )


def _gemini_models_to_try(primary: str) -> list[str]:
    models = [primary]
    for model in DEFAULT_GEMINI_FALLBACK_MODELS:
        if model not in models:
            models.append(model)
    return models


def _call_gemini_once(
    client,
    model: str,
    contents,
    system_instruction: str,
) -> _GeminiAttempt:
    from google.genai.errors import ClientError

    attempt = _GeminiAttempt(model=model)
    try:
        try:
            response = _generate_with_gemini(
                client,
                model,
                contents,
                system_instruction,
                use_thinking=True,
            )
        except ClientError as exc:
            status, body = _client_error_details(exc)
            attempt.status_code = status
            attempt.raw_body = body
            if _is_quota_error(exc):
                attempt.exception_caught = True
                attempt.exception_type = type(exc).__name__
                logger.error(
                    "Gemini quota/rate-limit for model=%s status=%s body=%s",
                    model,
                    status,
                    body,
                )
                _log_gemini_attempt(attempt)
                return attempt
            if not _is_thinking_config_error(exc):
                raise
            logger.warning(
                "Gemini rejected thinking_config for model=%s (%s); retrying without it.",
                model,
                exc,
            )
            response = _generate_with_gemini(
                client,
                model,
                contents,
                system_instruction,
                use_thinking=False,
            )

        attempt.status_code = 200
        attempt.finish_reason = _log_gemini_finish_reason(response)
        attempt.raw_text = _extract_candidate_text(response)
        attempt.raw_body = attempt.raw_text
        attempt.payload = _finalize_payload_from_raw(attempt.raw_text)

        # If thinking still consumed the shared token budget, retry once with more headroom.
        if attempt.finish_reason == "MAX_TOKENS":
            logger.warning(
                "Retrying Gemini once after MAX_TOKENS with max_output_tokens=%s.",
                MAX_OUTPUT_TOKENS * 2,
            )
            try:
                response = _generate_with_gemini(
                    client,
                    model,
                    contents,
                    system_instruction,
                    use_thinking=True,
                    max_output_tokens=MAX_OUTPUT_TOKENS * 2,
                )
            except ClientError as exc:
                if _is_thinking_config_error(exc):
                    response = _generate_with_gemini(
                        client,
                        model,
                        contents,
                        system_instruction,
                        use_thinking=False,
                        max_output_tokens=MAX_OUTPUT_TOKENS * 2,
                    )
                else:
                    raise
            attempt.finish_reason = _log_gemini_finish_reason(response)
            attempt.raw_text = _extract_candidate_text(response)
            attempt.raw_body = attempt.raw_text
            retry_payload = _finalize_payload_from_raw(attempt.raw_text)
            if retry_payload:
                attempt.payload = retry_payload
            if attempt.finish_reason == "MAX_TOKENS":
                logger.error(
                    "Gemini reply still truncated after retry (finish_reason=MAX_TOKENS)."
                )

        _log_gemini_attempt(attempt)
        return attempt
    except Exception as exc:
        status, body = _client_error_details(exc)
        attempt.status_code = status
        attempt.raw_body = body
        attempt.exception_caught = True
        attempt.exception_type = type(exc).__name__
        if status in {404, 400, 401, 403}:
            logger.error(
                "Gemini call failed for model=%s status=%s body=%s",
                model,
                status,
                body,
            )
        else:
            logger.exception(
                "Gemini call failed for model=%s status=%s body=%s",
                model,
                status,
                body,
            )
        _log_gemini_attempt(attempt)
        return attempt


def _call_gemini(
    message: str,
    user_context: str | None,
    history_messages: list[dict[str, str]] | None = None,
) -> tuple[dict | None, AssistantLLMUnavailable | None]:
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured.")
        return None, AssistantLLMUnavailable(
            "ai.not_configured",
            "The AI assistant is not configured. Please try again later.",
            503,
        )

    try:
        from google import genai
    except ImportError:
        logger.error(
            "google-genai is not installed. Run: pip install -r requirements.txt"
        )
        return None, AssistantLLMUnavailable(
            "ai.service_unavailable",
            "Something went wrong with the AI assistant. Please try again.",
            503,
        )

    # 60s gives thinking models room without leaving the client hanging forever.
    client = genai.Client(api_key=api_key, http_options={"timeout": 60_000})
    primary = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")
    raw_contents = build_gemini_contents(history_messages or [], message)
    contents = _to_gemini_content(raw_contents)
    system_instruction = build_system_instruction(user_context, message)

    last_error: AssistantLLMUnavailable | None = None
    saw_quota = False
    for model in _gemini_models_to_try(primary):
        attempt = _call_gemini_once(client, model, contents, system_instruction)
        if attempt.payload and attempt.payload.get("text"):
            return attempt.payload, None

        if attempt.status_code == 429 or (
            attempt.raw_body and "RESOURCE_EXHAUSTED" in (attempt.raw_body or "").upper()
        ):
            saw_quota = True
            last_error = AssistantLLMUnavailable(
                "ai.quota_exceeded",
                "The AI assistant is temporarily rate-limited. Please try again in a minute.",
                503,
            )
            # Try the next model — free-tier quotas are often per-model.
            continue

        if attempt.exception_caught:
            # Prefer an earlier quota error over a later model-not-found/etc.
            if not saw_quota:
                last_error = AssistantLLMUnavailable(
                    "ai.service_unavailable",
                    "Something went wrong with the AI assistant. Please try again.",
                    503,
                )
            continue

        # Successful HTTP but empty/unusable payload
        if not saw_quota:
            last_error = AssistantLLMUnavailable(
                "ai.service_unavailable",
                "Something went wrong with the AI assistant. Please try again.",
                503,
            )

    if saw_quota:
        return None, AssistantLLMUnavailable(
            "ai.quota_exceeded",
            "The AI assistant is temporarily rate-limited. Please try again in a minute.",
            503,
        )

    return None, last_error or AssistantLLMUnavailable(
        "ai.service_unavailable",
        "Something went wrong with the AI assistant. Please try again.",
        503,
    )


def _call_anthropic(
    message: str,
    user_context: str | None,
    history_messages: list[dict[str, str]] | None = None,
) -> tuple[dict | None, AssistantLLMUnavailable | None]:
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, AssistantLLMUnavailable(
            "ai.not_configured",
            "The AI assistant is not configured. Please try again later.",
            503,
        )

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
            system=build_system_instruction(user_context, message),
            messages=messages,
        )
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]
        raw = "\n".join(text_blocks).strip()
        payload = _finalize_payload_from_raw(raw)
        if payload and payload.get("text"):
            return payload, None
        return None, AssistantLLMUnavailable(
            "ai.service_unavailable",
            "Something went wrong with the AI assistant. Please try again.",
            503,
        )
    except Exception:
        logger.exception("Anthropic call failed.")
        return None, AssistantLLMUnavailable(
            "ai.service_unavailable",
            "Something went wrong with the AI assistant. Please try again.",
            503,
        )


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
) -> dict:
    """
    Return a structured assistant payload:
    {response_type: "answer"|"clarify", text: str, options: list[str]}

    Raises AssistantLLMUnavailable when no provider can produce a reply.
    """
    callers = {
        "gemini": _call_gemini,
        "anthropic": _call_anthropic,
    }

    providers = _provider_order()
    if not providers:
        logger.error("No AI provider configured (missing GEMINI_API_KEY / ANTHROPIC_API_KEY).")
        raise AssistantLLMUnavailable(
            "ai.not_configured",
            "The AI assistant is not configured. Please try again later.",
            503,
        )

    last_error: AssistantLLMUnavailable | None = None
    for provider in providers:
        payload, error = callers[provider](message, user_context, history_messages)
        if payload and payload.get("text"):
            logger.info(
                "AI assistant reply generated via %s "
                "(type=%s options=%s prior_turns=%s history_limit=%s).",
                provider,
                payload.get("response_type"),
                len(payload.get("options") or []),
                len(history_messages or []),
                CONVERSATION_HISTORY_LIMIT,
            )
            return payload
        last_error = error

    raise last_error or AssistantLLMUnavailable(
        "ai.service_unavailable",
        "Something went wrong with the AI assistant. Please try again.",
        503,
    )


def fallback_assistant_payload(text: str) -> dict:
    """Kept for tests/tools — must NOT be used as a silent chat substitute."""
    return normalize_assistant_payload(
        {"response_type": "answer", "text": sanitize_assistant_reply(text)}
    )
