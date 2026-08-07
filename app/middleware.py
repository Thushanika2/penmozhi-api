from datetime import datetime, timezone
from functools import wraps

from flask_jwt_extended import (
    current_user,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)

from app.api_responses import error_response


def _check_user_session(user):
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    try:
        request_user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return error_response("auth.invalid_token", "Invalid authentication token.", 401)

    if user.id != request_user_id:
        return error_response("auth.invalid_token", "Invalid authentication token.", 401)

    status = getattr(user, "status", "active")
    if status != "active":
        if status == "suspended":
            return error_response(
                "auth.account_suspended",
                "Your account has been suspended. Please contact support.",
                403,
            )
        if status == "banned":
            return error_response(
                "auth.account_banned",
                "Your account has been banned.",
                403,
            )
        return error_response(
            "auth.account_inactive",
            "Your account is not active.",
            403,
        )

    token_valid_after = getattr(user, "token_valid_after", None)
    if token_valid_after:
        claims = get_jwt()
        issued_at = claims.get("iat")
        if issued_at is not None:
            token_issued = datetime.fromtimestamp(issued_at, tz=timezone.utc)
            valid_after = token_valid_after
            if valid_after.tzinfo is None:
                valid_after = valid_after.replace(tzinfo=timezone.utc)
            if token_issued < valid_after:
                return error_response(
                    "auth.session_expired",
                    "Your session has expired. Please sign in again.",
                    401,
                )

    return None


def jwt_required_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if not current_user:
            return error_response("auth.user_not_found", "User not found.", 404)
        session_error = _check_user_session(current_user)
        if session_error:
            return session_error
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if not current_user:
                return error_response("auth.user_not_found", "User not found.", 404)
            session_error = _check_user_session(current_user)
            if session_error:
                return session_error
            if current_user.role not in roles:
                return error_response(
                    "auth.forbidden",
                    "Access forbidden: insufficient permissions.",
                    403,
                )
            # Dashboard/app APIs require completed onboarding for regular users.
            if (
                current_user.role == "user"
                and "user" in roles
                and not getattr(current_user, "onboarding_completed", False)
            ):
                return error_response(
                    "onboarding.incomplete",
                    "Please complete onboarding before using the app.",
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
