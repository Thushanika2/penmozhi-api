from functools import wraps

from flask import jsonify
from flask_jwt_extended import current_user, verify_jwt_in_request


def jwt_required_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if not current_user:
            return jsonify({"error": "User not found."}), 404
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if not current_user:
                return jsonify({"error": "User not found."}), 404
            if current_user.role not in roles:
                return jsonify({"error": "Access forbidden: insufficient permissions."}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
