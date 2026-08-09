from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.push_subscription_model import PushSubscription


def _get_owned_push_subscription(subscription_id):
    sub = db.session.get(PushSubscription, subscription_id)
    if not sub:
        return None, error_response("push_subscriptions.not_found", "Push subscription not found.", 404)
    if sub.profile_id != current_user.id:
        return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    return sub, None


def _validate_push_subscription_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    for field in ("endpoint", "p256dh", "auth"):
        if data.get(field) is None or str(data.get(field)).strip() == "":
            errors.append(f"{field} is required.")

    return errors


def create_push_subscription():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_push_subscription_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    endpoint = str(data.get("endpoint")).strip()
    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()

    try:
        if existing:
            existing.profile_id = current_user.id
            existing.p256dh = str(data.get("p256dh")).strip()
            existing.auth = str(data.get("auth")).strip()
            existing.device_type = (
                str(data.get("device_type")).strip() if data.get("device_type") else None
            )
            sub = existing
        else:
            sub = PushSubscription(
                profile_id=current_user.id,
                endpoint=endpoint,
                p256dh=str(data.get("p256dh")).strip(),
                auth=str(data.get("auth")).strip(),
                device_type=str(data.get("device_type")).strip() if data.get("device_type") else None,
            )
            db.session.add(sub)

        db.session.commit()
        return message_response(
            "push_subscriptions.created_success",
            "Push subscription registered successfully.",
            201,
            push_subscription=sub.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_push_subscription(subscription_id):
    sub, error = _get_owned_push_subscription(subscription_id)
    if error:
        return error

    try:
        db.session.delete(sub)
        db.session.commit()
        return message_response(
            "push_subscriptions.deleted_success",
            "Push subscription removed successfully.",
            200,
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def unsubscribe_push_subscription():
    data = request.get_json(silent=True) or {}
    endpoint = str(data.get("endpoint", "")).strip()
    if not endpoint:
        return validation_errors(
            [("validation.invalid_payload", "endpoint is required.")], 400
        )

    try:
        PushSubscription.query.filter_by(
            profile_id=current_user.id, endpoint=endpoint
        ).delete(synchronize_session=False)
        db.session.commit()
        return message_response(
            "push_subscriptions.deleted_success",
            "Push subscription removed successfully.",
            200,
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
