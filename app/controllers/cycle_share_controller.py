import json

from flask import current_app, jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.cycle_share_model import CycleShare
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.daily_log_model import DailyLog
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.models.user_profile_model import UserProfile
from app.services.email_service import send_cycle_share_invite_email


def _get_owned_cycle_share(share_id):
    share = db.session.get(CycleShare, share_id)
    if not share:
        return None, error_response("cycle_shares.not_found", "Cycle share not found.", 404)
    if share.owner_profile_id != current_user.id:
        return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    return share, None


def _validate_cycle_share_payload(data):
    errors = []
    if not data:
        return ["Request body is required."]

    if data.get("shared_with_email") is None or str(data.get("shared_with_email")).strip() == "":
        errors.append("shared_with_email is required.")

    return errors


def create_cycle_share():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_cycle_share_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    email = str(data.get("shared_with_email")).strip().lower()
    if email == current_user.email.lower():
        return validation_errors(
            [("validation.cannot_share_self", "You cannot share with your own email.")],
            400,
        )

    permissions = data.get("permissions") or {"cycle": True, "symptoms": False}
    if not isinstance(permissions, dict):
        return validation_errors([("validation.permissions_object", "permissions must be an object.")], 400)

    try:
        share = CycleShare(
            owner_profile_id=current_user.id,
            shared_with_email=email,
            status="pending",
            permissions=permissions,
        )
        db.session.add(share)
        db.session.commit()

        send_cycle_share_invite_email(
            to_email=email,
            owner_name=current_user.full_name,
            share_id=share.id,
        )

        return message_response(
            "cycle_shares.created_success",
            "Cycle share invitation sent successfully.",
            201,
            cycle_share=share.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def list_cycle_shares():
    owned = (
        CycleShare.query.filter_by(owner_profile_id=current_user.id)
        .order_by(CycleShare.created_at.desc())
        .all()
    )
    received = (
        CycleShare.query.filter(
            (CycleShare.shared_with_profile_id == current_user.id)
            | (
                (CycleShare.shared_with_email == current_user.email)
                & (CycleShare.status.in_(["pending", "accepted"]))
            )
        )
        .order_by(CycleShare.created_at.desc())
        .all()
    )

    seen = set()
    combined = []
    for share in owned + received:
        if share.id not in seen:
            seen.add(share.id)
            combined.append(share)

    return jsonify({"cycle_shares": [s.to_dict() for s in combined]}), 200


def accept_cycle_share(share_id):
    share = db.session.get(CycleShare, share_id)
    if not share:
        return error_response("cycle_shares.not_found", "Cycle share not found.", 404)

    if share.shared_with_email.lower() != current_user.email.lower():
        return error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)

    if share.status != "pending":
        return error_response("cycle_shares.not_pending", "This invitation is no longer pending.", 400)

    try:
        share.status = "accepted"
        share.shared_with_profile_id = current_user.id
        db.session.commit()
        return message_response(
            "cycle_shares.accepted_success",
            "Cycle share accepted successfully.",
            200,
            cycle_share=share.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_cycle_share(share_id):
    share, error = _get_owned_cycle_share(share_id)
    if error:
        return error

    try:
        share.status = "revoked"
        db.session.commit()
        return message_response("cycle_shares.revoked_success", "Cycle share revoked successfully.", 200)
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def view_cycle_share(share_id):
    share = db.session.get(CycleShare, share_id)
    if not share:
        return error_response("cycle_shares.not_found", "Cycle share not found.", 404)

    if share.status != "accepted":
        return error_response("cycle_shares.not_accepted", "This share is not active.", 403)

    if share.shared_with_profile_id != current_user.id:
        return error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)

    owner = db.session.get(UserProfile, share.owner_profile_id)
    if not owner:
        return error_response("auth.user_not_found", "Owner not found.", 404)

    permissions = share.permissions or {}
    payload = {
        "cycle_share": share.to_dict(),
        "owner_name": owner.full_name,
    }

    if permissions.get("cycle"):
        cycles = (
            CycleHistoryLog.query.filter_by(profile_id=owner.id)
            .order_by(CycleHistoryLog.cycle_start_date.desc())
            .limit(12)
            .all()
        )
        payload["cycles"] = [c.to_dict() for c in cycles]

    if permissions.get("symptoms"):
        symptoms = (
            SymptomTrackingLog.query.filter_by(profile_id=owner.id)
            .order_by(SymptomTrackingLog.date_time.desc())
            .limit(30)
            .all()
        )
        payload["symptoms"] = [s.to_dict() for s in symptoms]

    if permissions.get("daily_logs"):
        logs = (
            DailyLog.query.filter_by(profile_id=owner.id)
            .order_by(DailyLog.log_date.desc())
            .limit(30)
            .all()
        )
        payload["daily_logs"] = [log.to_dict() for log in logs]

    return jsonify(payload), 200
