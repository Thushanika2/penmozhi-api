from functools import wraps

from flask_jwt_extended import current_user, verify_jwt_in_request

from app.api_responses import error_response


def jwt_required_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if not current_user:
            return error_response("auth.user_not_found", "User not found.", 404)
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if not current_user:
                return error_response("auth.user_not_found", "User not found.", 404)
            if current_user.role not in roles:
                return error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
