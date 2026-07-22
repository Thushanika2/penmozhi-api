import re

from flask import jsonify, request
from flask_jwt_extended import create_access_token, current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.user_profile_model import UserProfile
from app.utils import LANGUAGE_PREFERENCES, parse_date


def _validate_register_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    full_name = data.get("full_name")
    if full_name is None or str(full_name).strip() == "":
        errors.append("full_name is required.")

    email = data.get("email")
    if email is None or str(email).strip() == "":
        errors.append("email is required.")
    else:
        email_str = str(email).strip()
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email_str):
            errors.append("Invalid email format.")
        elif UserProfile.query.filter_by(email=email_str).first():
            errors.append("Email address already exists.")

    password = data.get("password")
    if password is None or str(password).strip() == "":
        errors.append("password is required.")
    elif len(str(password)) < 6:
        errors.append("password must be at least 6 characters long.")

    date_of_birth = data.get("date_of_birth")
    if date_of_birth is None or str(date_of_birth).strip() == "":
        errors.append("date_of_birth is required.")
    else:
        try:
            parse_date(date_of_birth)
        except ValueError:
            errors.append("date_of_birth must be a valid date (YYYY-MM-DD).")

    language = str(data.get("language_preference", "english")).strip().lower() or "english"
    if language not in LANGUAGE_PREFERENCES:
        errors.append("language_preference must be 'tamil' or 'english'.")

    role = str(data.get("role", "user")).strip().lower() or "user"
    if role == "admin":
        errors.append("Admin accounts can only be created via database seeders.")
    elif role != "user":
        errors.append("role must be 'user'.")

    return errors


def _validate_login_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    if data.get("email") is None or str(data.get("email")).strip() == "":
        errors.append("email is required.")

    if data.get("password") is None or str(data.get("password")).strip() == "":
        errors.append("password is required.")

    return errors


def register():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_register_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        user = UserProfile(
            full_name=str(data.get("full_name")).strip(),
            date_of_birth=parse_date(data.get("date_of_birth")),
            email=str(data.get("email")).strip(),
            language_preference=str(
                data.get("language_preference", "english")
            ).strip().lower() or "english",
            role="user",
        )
        user.set_password(str(data.get("password")))
        db.session.add(user)
        db.session.flush()

        health_profile = HealthProfile(profile_id=user.id)
        db.session.add(health_profile)
        db.session.flush()

        pcos_status = PCOSDisorderStatus(
            health_profile_id=health_profile.id,
            disorder_type="none",
            diagnosis_status="not_diagnosed",
        )
        db.session.add(pcos_status)
        db.session.commit()

        return jsonify({
            "message": "User registered successfully.",
            "user": user.to_dict(),
            "health_profile": health_profile.to_dict(),
        }), 201
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def login():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_login_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        email_str = str(data.get("email")).strip()
        user = UserProfile.query.filter_by(email=email_str).first()

        if not user or not user.check_password(str(data.get("password"))):
            return error_response("auth.invalid_credentials", "Invalid email or password.", 401)

        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "message": "Login successful.",
            "access_token": access_token,
            "user": user.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def logout():
    return message_response("auth.logout_success", "Logout successful.", 200)


def profile():
    user = current_user
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    payload = {"user": user.to_dict()}
    if user.health_profile:
        payload["health_profile"] = user.health_profile.to_dict()

    return jsonify(payload), 200


def update_profile():
    user = current_user
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    language = data.get("language_preference")
    if language is None:
        return validation_errors([("validation.language_required", "language_preference is required.")], 400)

    language = str(language).strip().lower()
    if language not in LANGUAGE_PREFERENCES:
        return validation_errors([("validation.language_invalid", "language_preference must be 'tamil' or 'english'.")], 400)

    try:
        user.language_preference = language
        db.session.commit()
        return message_response(
            "auth.profile_updated",
            "Profile updated successfully.",
            200,
            user=user.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
