from flask import current_app, jsonify, redirect, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response
from app.extensions import db
from app.models.wearable_connection_model import WearableConnection
from app.services.privacy_service import record_wearable_consent
from app.utils import utc_now

ALLOWED_PROVIDERS = {"oura", "whoop", "fitbit", "withings", "garmin", "apple"}


def _get_owned_wearable(provider):
    conn = WearableConnection.query.filter_by(
        profile_id=current_user.id,
        provider=provider,
    ).first()
    if not conn:
        return None, error_response("wearables.not_found", "Wearable connection not found.", 404)
    return conn, None


def connect_wearable(provider):
    provider = str(provider).lower().strip()
    if provider not in ALLOWED_PROVIDERS:
        return error_response("wearables.invalid_provider", "Unsupported wearable provider.", 400)

    # TODO: Implement real OAuth flow for each provider using env credentials.
    client_url = current_app.config.get("CLIENT_APP_URL", "http://localhost:3000").rstrip("/")
    return jsonify({
        "message": "Wearable OAuth is not yet configured.",
        "message_code": "wearables.oauth_stub",
        "provider": provider,
        "redirect_url": f"{client_url}/dashboard/wearables?provider={provider}&status=stub",
        "todo": (
            f"Configure {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET "
            "and implement OAuth authorization URL generation."
        ),
    }), 200


def callback_wearable(provider):
    provider = str(provider).lower().strip()
    if provider not in ALLOWED_PROVIDERS:
        return error_response("wearables.invalid_provider", "Unsupported wearable provider.", 400)

    # TODO: Exchange authorization code for tokens and store encrypted at rest.
    code = request.args.get("code")
    if not code:
        return error_response("wearables.missing_code", "Authorization code missing.", 400)

    try:
        conn = WearableConnection.query.filter_by(
            profile_id=current_user.id,
            provider=provider,
        ).first()
        if not conn:
            conn = WearableConnection(
                profile_id=current_user.id,
                provider=provider,
            )
            db.session.add(conn)

        # Placeholder tokens — replace with encrypted real tokens from OAuth exchange.
        conn.access_token = f"stub_access_{code[:8]}"
        conn.refresh_token = f"stub_refresh_{code[:8]}"
        conn.last_synced_at = utc_now()
        record_wearable_consent(current_user.id, provider)
        db.session.commit()

        client_url = current_app.config.get("CLIENT_APP_URL", "http://localhost:3000").rstrip("/")
        return redirect(f"{client_url}/dashboard/wearables?provider={provider}&status=connected")
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def disconnect_wearable(provider):
    provider = str(provider).lower().strip()
    conn, error = _get_owned_wearable(provider)
    if error:
        return error

    try:
        db.session.delete(conn)
        db.session.commit()
        return message_response(
            "wearables.disconnected_success",
            "Wearable disconnected successfully.",
            200,
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_my_wearables():
    connections = (
        WearableConnection.query.filter_by(profile_id=current_user.id)
        .order_by(WearableConnection.provider.asc())
        .all()
    )
    return jsonify({"wearable_connections": [c.to_dict() for c in connections]}), 200
