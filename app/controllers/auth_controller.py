import secrets
from datetime import timedelta

from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, current_user
from marshmallow import ValidationError as MarshmallowValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.password_reset_token_model import PasswordResetToken
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.user_profile_model import UserProfile
from app.schemas.auth_schema import (
    ForgotPasswordSchema,
    LoginSchema,
    RefreshTokenSchema,
    RegisterSchema,
    ResetPasswordSchema,
    UpdateProfileSchema,
)
from app.utils import LANGUAGE_PREFERENCES, parse_date, utc_now


def _issue_tokens(user):
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return access_token, refresh_token


def _schema_errors(schema_err):
    return validation_errors(
        [("validation.invalid_payload", str(msg)) for msgs in schema_err.messages.values() for msg in msgs],
        400,
    )


def register():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    schema = RegisterSchema()
    try:
        validated = schema.load(data)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    email_str = str(validated["email"]).strip()
    if UserProfile.query.filter_by(email=email_str).first():
        return validation_errors([("validation.email_exists", "Email address already exists.")], 400)

    language = str(validated.get("language_preference", "english")).strip().lower() or "english"
    if language not in LANGUAGE_PREFERENCES:
        return validation_errors(
            [("validation.language_invalid", "language_preference must be 'tamil' or 'english'.")],
            400,
        )

    try:
        user = UserProfile(
            full_name=str(validated["full_name"]).strip(),
            date_of_birth=validated["date_of_birth"],
            email=email_str,
            language_preference=language,
            role="user",
            onboarding_completed=False,
        )
        user.set_password(str(validated["password"]))
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

    schema = LoginSchema()
    try:
        validated = schema.load(data)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    try:
        email_str = str(validated["email"]).strip()
        user = UserProfile.query.filter_by(email=email_str).first()

        if not user or not user.check_password(str(validated["password"])):
            return error_response("auth.invalid_credentials", "Invalid email or password.", 401)

        access_token, refresh_token = _issue_tokens(user)
        return jsonify({
            "message": "Login successful.",
            "access_token": access_token,
            "refresh_token": refresh_token,
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


def refresh():
    data = request.get_json(silent=True) or {}
    schema = RefreshTokenSchema()
    try:
        validated = schema.load(data)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    from flask_jwt_extended import decode_token

    try:
        decoded = decode_token(validated["refresh_token"])
        user_id = int(decoded["sub"])
        user = db.session.get(UserProfile, user_id)
        if not user:
            return error_response("auth.user_not_found", "User not found.", 404)

        access_token, refresh_token = _issue_tokens(user)
        return jsonify({
            "message_code": "auth.token_refreshed",
            "message": "Token refreshed successfully.",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        }), 200
    except Exception:
        return error_response("auth.invalid_refresh_token", "Invalid or expired refresh token.", 401)


def forgot_password():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    schema = ForgotPasswordSchema()
    try:
        validated = schema.load(data)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    email_str = str(validated["email"]).strip()
    user = UserProfile.query.filter_by(email=email_str).first()

    response = {
        "message_code": "auth.reset_email_sent",
        "message": "If an account exists for this email, a reset link has been sent.",
    }

    if not user:
        return jsonify(response), 200

    raw_token = secrets.token_urlsafe(32)
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=generate_password_hash(raw_token),
        expires_at=utc_now() + timedelta(hours=1),
    )
    db.session.add(token)
    db.session.commit()

    if current_app.config.get("DEBUG"):
        response["reset_token"] = raw_token

    return jsonify(response), 200


def reset_password():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    schema = ResetPasswordSchema()
    try:
        validated = schema.load(data)
    except MarshmallowValidationError as err:
        return _schema_errors(err)

    now = utc_now()
    tokens = (
        PasswordResetToken.query.filter(
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .order_by(PasswordResetToken.created_at.desc())
        .all()
    )

    matched = None
    for entry in tokens:
        if check_password_hash(entry.token_hash, validated["token"]):
            matched = entry
            break

    if not matched:
        return error_response("auth.invalid_reset_token", "Invalid or expired reset token.", 400)

    user = db.session.get(UserProfile, matched.user_id)
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    try:
        user.set_password(str(validated["password"]))
        matched.used_at = now
        db.session.commit()
        return message_response(
            "auth.password_reset_success",
            "Password reset successfully. You can now sign in.",
            200,
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
