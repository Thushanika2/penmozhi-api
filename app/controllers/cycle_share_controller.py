from datetime import timedelta
import secrets

from flask import jsonify, request
from flask_jwt_extended import current_user
from sqlalchemy.exc import IntegrityError
from marshmallow import ValidationError, validate
from werkzeug.security import check_password_hash, generate_password_hash

from app.api_responses import error_response, message_response
from app.extensions import db
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.sharing_model import SharedConnection, SharingInvite
from app.models.user_profile_model import UserProfile
from app.services.cycle_prediction_service import compute_cycle_insights
from app.services.email_service import send_cycle_invitation_email
from app.services.privacy_service import record_consent
from app.utils import utc_now

INVITE_LIFETIME_MINUTES = 10
INVITE_RESEND_COOLDOWN_SECONDS = 60
MAX_VERIFICATION_ATTEMPTS = 5
GENERIC_CODE_ERROR = "Invalid or expired invitation code."


def _active_connection(column, user_id):
    return SharedConnection.query.filter(column == user_id, SharedConnection.status == "active").first()


def _normalized_email(value):
    email = str(value or "").strip().lower()
    try:
        validate.Email()(email)
    except ValidationError:
        return None
    return email if len(email) <= 120 else None


def send_invitation():
    data = request.get_json(silent=True) or {}
    invited_email = _normalized_email(data.get("email"))
    if not invited_email:
        return error_response("invitations.invalid_email", "Enter a valid email address.", 400)
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
    latest = (
        SharingInvite.query.filter_by(
            invited_email=invited_email,
            status="active",
        )
        .order_by(SharingInvite.created_at.desc())
        .with_for_update()
        .first()
    )
    if latest:
        created_at = latest.created_at
        if created_at.tzinfo is None and now.tzinfo is not None:
            created_at = created_at.replace(tzinfo=now.tzinfo)
        retry_after = INVITE_RESEND_COOLDOWN_SECONDS - int((now - created_at).total_seconds())
        if retry_after > 0:
            return jsonify({
                "error": "Please wait before requesting another invitation.",
                "error_code": "invitations.cooldown",
                "retry_after": retry_after,
            }), 429

    raw_code = f"{secrets.randbelow(1_000_000):06d}"
    invite = SharingInvite(
        invited_email=invited_email,
        code_hash=generate_password_hash(raw_code),
        sharer_user_id=current_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=INVITE_LIFETIME_MINUTES),
        status="active",
        verification_attempts=0,
    )
    try:
        db.session.add(invite)
        db.session.flush()
        if not send_cycle_invitation_email(invited_email, raw_code):
            db.session.rollback()
            return error_response(
                "invitations.delivery_failed",
                "Invitation could not be sent. Please try again later.",
                503,
            )
        SharingInvite.query.filter(
            SharingInvite.invited_email == invited_email,
            SharingInvite.status == "active",
            SharingInvite.id != invite.id,
        ).update({"status": "invalidated"}, synchronize_session=False)
        record_consent(current_user.id, "cycle_date_sharing", context="email invitation")
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
    return jsonify({
        "message": "Invitation sent successfully. Please check the email for your invitation code.",
        "expires_in": INVITE_LIFETIME_MINUTES * 60,
        "resend_after": INVITE_RESEND_COOLDOWN_SECONDS,
    }), 200


def verify_invitation():
    data = request.get_json(silent=True) or {}
    email = _normalized_email(data.get("email"))
    code = str(data.get("code", "")).strip()
    if not email or len(code) != 6 or not code.isdigit():
        return error_response("invitations.invalid_code", GENERIC_CODE_ERROR, 400)

    now = utc_now()
    invite = (
        SharingInvite.query.filter_by(invited_email=email, status="active")
        .order_by(SharingInvite.created_at.desc())
        .with_for_update()
        .first()
    )
    if not invite:
        return error_response("invitations.invalid_code", GENERIC_CODE_ERROR, 400)
    expires_at = invite.expires_at
    if expires_at.tzinfo is None and now.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    invalid = (
        expires_at <= now
        or invite.used_at is not None
        or invite.verification_attempts >= MAX_VERIFICATION_ATTEMPTS
        or current_user.email.strip().lower() != email
        or not check_password_hash(invite.code_hash, code)
    )
    if invalid:
        invite.verification_attempts += 1
        if expires_at <= now or invite.verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
            invite.status = "invalidated"
        db.session.commit()
        return error_response("invitations.invalid_code", GENERIC_CODE_ERROR, 400)
    if invite.sharer_user_id == current_user.id:
        return error_response("invitations.invalid_code", GENERIC_CODE_ERROR, 400)
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
    invite.status = "used"
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


def resend_invitation():
    email = _normalized_email((request.get_json(silent=True) or {}).get("email"))
    if not email or current_user.email.strip().lower() != email:
        return error_response("invitations.invalid_code", GENERIC_CODE_ERROR, 400)
    previous = (
        SharingInvite.query.filter_by(invited_email=email, status="active")
        .order_by(SharingInvite.created_at.desc())
        .with_for_update()
        .first()
    )
    if not previous:
        return error_response("invitations.invalid_code", GENERIC_CODE_ERROR, 400)
    now = utc_now()
    created_at = previous.created_at
    if created_at.tzinfo is None and now.tzinfo is not None:
        created_at = created_at.replace(tzinfo=now.tzinfo)
    retry_after = INVITE_RESEND_COOLDOWN_SECONDS - int((now - created_at).total_seconds())
    if retry_after > 0:
        return jsonify({
            "error": "Please wait before requesting another invitation.",
            "error_code": "invitations.cooldown",
            "retry_after": retry_after,
        }), 429

    raw_code = f"{secrets.randbelow(1_000_000):06d}"
    replacement = SharingInvite(
        invited_email=email,
        code_hash=generate_password_hash(raw_code),
        sharer_user_id=previous.sharer_user_id,
        created_at=now,
        expires_at=now + timedelta(minutes=INVITE_LIFETIME_MINUTES),
        status="active",
        verification_attempts=0,
    )
    try:
        db.session.add(replacement)
        db.session.flush()
        if not send_cycle_invitation_email(email, raw_code):
            db.session.rollback()
            return error_response(
                "invitations.delivery_failed",
                "Invitation could not be sent. Please try again later.",
                503,
            )
        previous.status = "invalidated"
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
    return jsonify({
        "message": "Invitation sent successfully. Please check the email for your invitation code.",
        "expires_in": INVITE_LIFETIME_MINUTES * 60,
        "resend_after": INVITE_RESEND_COOLDOWN_SECONDS,
    }), 200


def create_invite():
    return send_invitation()


def connect_with_code():
    return verify_invitation()


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
