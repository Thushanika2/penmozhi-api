from datetime import timedelta
import secrets

from flask import jsonify, request
from flask_jwt_extended import current_user
from sqlalchemy.exc import IntegrityError

from app.api_responses import error_response, message_response
from app.extensions import db
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.sharing_model import SharedConnection, SharingInvite
from app.models.user_profile_model import UserProfile
from app.services.cycle_prediction_service import compute_cycle_insights
from app.services.privacy_service import record_consent
from app.utils import utc_now

INVITE_LIFETIME_MINUTES = 15


def _active_connection(column, user_id):
    return SharedConnection.query.filter(column == user_id, SharedConnection.status == "active").first()


def create_invite():
    data = request.get_json(silent=True) or {}
    if data.get("consent") is not True:
        return error_response(
            "cycle_sharing.consent_required",
            "You must agree to share only your cycle dates before generating a code.",
            400,
        )
    if _active_connection(SharedConnection.sharer_user_id, current_user.id):
        return error_response(
            "cycle_sharing.already_sharing",
            "Disconnect your current viewer before creating a new invite.",
            409,
        )

    now = utc_now()
    invite = SharingInvite(
        code=secrets.token_urlsafe(9),
        sharer_user_id=current_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=INVITE_LIFETIME_MINUTES),
    )
    db.session.add(invite)
    record_consent(current_user.id, "cycle_date_sharing", context="one-time sharing invite")
    db.session.commit()
    return jsonify({"invite": invite.to_dict(include_code=True)}), 201


def connect_with_code():
    code = str((request.get_json(silent=True) or {}).get("code", "")).strip()
    if not code:
        return error_response("cycle_sharing.code_required", "Invite code is required.", 400)

    invite = SharingInvite.query.filter_by(code=code).with_for_update().first()
    if not invite:
        return error_response("cycle_sharing.invalid_code", "Invite code is invalid.", 404)
    now = utc_now()
    if invite.used_at:
        return error_response("cycle_sharing.code_used", "Invite code has already been used.", 409)
    expires_at = invite.expires_at
    if expires_at.tzinfo is None and now.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        return error_response("cycle_sharing.code_expired", "Invite code has expired.", 410)
    if invite.sharer_user_id == current_user.id:
        return error_response("cycle_sharing.cannot_connect_self", "You cannot use your own invite code.", 400)
    if _active_connection(SharedConnection.sharer_user_id, invite.sharer_user_id):
        return error_response("cycle_sharing.sharer_busy", "This person is already sharing with someone.", 409)
    if _active_connection(SharedConnection.viewer_user_id, current_user.id):
        return error_response(
            "cycle_sharing.viewer_busy", "Disconnect your current shared cycle before connecting.", 409
        )

    connection = SharedConnection(
        sharer_user_id=invite.sharer_user_id,
        viewer_user_id=current_user.id,
        active_sharer_user_id=invite.sharer_user_id,
        active_viewer_user_id=current_user.id,
        status="active",
        connected_at=now,
    )
    invite.used_at = now
    invite.used_by_user_id = current_user.id
    db.session.add(connection)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response(
            "cycle_sharing.connection_conflict",
            "The sharer or viewer already has an active connection.",
            409,
        )
    return jsonify({"connection": connection.to_dict(current_user.id)}), 201


def list_connections():
    connections = SharedConnection.query.filter(
        (SharedConnection.sharer_user_id == current_user.id)
        | (SharedConnection.viewer_user_id == current_user.id)
    ).order_by(SharedConnection.connected_at.desc()).all()
    return jsonify({"connections": [item.to_dict(current_user.id) for item in connections]}), 200


def disconnect(connection_id):
    connection = db.session.get(SharedConnection, connection_id)
    if not connection:
        return error_response("cycle_sharing.not_found", "Connection not found.", 404)
    if current_user.id not in (connection.sharer_user_id, connection.viewer_user_id):
        return error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    if connection.status != "active":
        return error_response("cycle_sharing.already_disconnected", "Connection is already disconnected.", 409)
    connection.status = "disconnected"
    connection.disconnected_at = utc_now()
    connection.active_sharer_user_id = None
    connection.active_viewer_user_id = None
    db.session.commit()
    return message_response("cycle_sharing.disconnected", "Connection disconnected.", 200)


def view_shared_cycle(connection_id):
    # This status query is deliberately performed on every request; shared data is never cached.
    connection = SharedConnection.query.filter_by(id=connection_id, status="active").first()
    if not connection:
        return error_response("cycle_sharing.inactive", "This connection is not active.", 403)
    if connection.viewer_user_id != current_user.id:
        return error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)

    owner = db.session.get(UserProfile, connection.sharer_user_id)
    periods = (
        db.session.query(CycleHistoryLog.cycle_start_date, CycleHistoryLog.cycle_end_date)
        .filter(CycleHistoryLog.profile_id == connection.sharer_user_id)
        .order_by(CycleHistoryLog.cycle_start_date.desc())
        .limit(12)
        .all()
    )
    insights = compute_cycle_insights(owner)
    # Strict allowlist: never serialize a cycle model, daily log, symptom, note, or AI record here.
    predictions = {
        "fertile_window_start": insights.get("fertile_window_start"),
        "fertile_window_end": insights.get("fertile_window_end"),
        "ovulation_date": insights.get("ovulation_date"),
        "pms_window_start": insights.get("pms_window_start"),
        "pms_window_end": insights.get("pms_window_end"),
    }
    return jsonify({
        "connection": connection.to_dict(current_user.id),
        "periods": [
            {"period_start_date": start.isoformat(), "period_end_date": end.isoformat()}
            for start, end in periods
        ],
        "predictions": predictions,
    }), 200


# Legacy entry points are intentionally disabled so old accepted shares cannot bypass the safeguards.
def legacy_disabled(*_args, **_kwargs):
    return error_response(
        "cycle_sharing.legacy_disabled",
        "This sharing flow has been retired. Generate a new one-time invite code.",
        410,
    )
