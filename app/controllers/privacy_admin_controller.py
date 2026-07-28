from flask import jsonify, request
from flask_jwt_extended import current_user
from sqlalchemy import func

from app.api_responses import error_response, message_response
from app.extensions import db
from app.models.privacy_request_model import PrivacyRequest
from app.models.push_subscription_model import PushSubscription
from app.models.user_consent_model import UserConsent
from app.models.user_profile_model import UserProfile
from app.models.wearable_connection_model import WearableConnection
from app.models.ai_health_assistant_session_model import AIHealthAssistantSession
from app.services.privacy_service import (
    INTEGRATION_CATALOG,
    USER_DATA_TABLES,
    complete_privacy_request,
)


def list_privacy_requests():
    status = request.args.get("status")
    query = PrivacyRequest.query.order_by(PrivacyRequest.created_at.desc())
    if status:
        query = query.filter_by(status=status.strip().lower())

    requests = query.all()
    return jsonify({"privacy_requests": [row.to_dict() for row in requests]}), 200


def complete_privacy_request_handler(request_id: int):
    request_row = db.session.get(PrivacyRequest, request_id)
    if not request_row:
        return error_response("privacy.request_not_found", "Privacy request not found.", 404)

    if request_row.status == "completed":
        return error_response("privacy.already_completed", "This request is already completed.", 409)

    try:
        complete_privacy_request(request_row, current_user.id)
        db.session.commit()
        return jsonify({
            "message": "Privacy request marked as completed.",
            "privacy_request": request_row.to_dict(),
            "deletion_approach": "hard_delete",
            "tables_affected": list(USER_DATA_TABLES),
        }), 200
    except ValueError as exc:
        db.session.rollback()
        return error_response("privacy.invalid_request", str(exc), 400)
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def list_integration_audit():
    wearable_counts = dict(
        db.session.query(WearableConnection.provider, func.count(WearableConnection.id))
        .group_by(WearableConnection.provider)
        .all()
    )
    push_count = PushSubscription.query.count()
    ai_users = (
        db.session.query(func.count(func.distinct(AIHealthAssistantSession.profile_id))).scalar()
        or 0
    )

    integrations = []
    for entry in INTEGRATION_CATALOG:
        provider = entry["provider"]
        if provider == "web_push":
            connected_users = push_count
        elif provider in {"google_gemini", "anthropic"}:
            connected_users = ai_users
        else:
            connected_users = wearable_counts.get(provider, 0)

        integrations.append(
            {
                **entry,
                "connected_users": connected_users,
                "status": "active" if connected_users > 0 or provider in {"google_gemini", "anthropic"} else "available",
            }
        )

    return jsonify({"integrations": integrations}), 200


def get_user_consents(user_id: int):
    user = db.session.get(UserProfile, user_id)
    if not user:
        return error_response("auth.user_not_found", "User not found.", 404)

    consents = (
        UserConsent.query.filter_by(user_id=user_id)
        .order_by(UserConsent.granted_at.desc())
        .all()
    )
    return jsonify({
        "user_id": user_id,
        "user_email": user.email,
        "consents": [consent.to_dict() for consent in consents],
    }), 200
