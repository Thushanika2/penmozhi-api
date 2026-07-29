import csv
import io
import logging

from flask import jsonify, make_response, request
from flask_jwt_extended import current_user
from sqlalchemy import or_

from app.api_responses import error_response, validation_errors
from app.extensions import db
from app.models.user_profile_model import UserProfile
from app.services.admin_user_service import (
    USER_STATUSES,
    action_log_rows,
    consent_rows,
    find_test_account_candidates,
    get_target_user,
    log_admin_action,
    subscription_label,
    user_detail_dict,
    user_list_dict,
)
from app.services.privacy_service import create_privacy_request
from app.utils import utc_now

logger = logging.getLogger(__name__)


def _commit_or_error(action: str):
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Admin user action failed: %s", action)
        return error_response("server.internal_error", "An internal server error occurred.", 500)
    return None


def list_users():
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(max(1, request.args.get("per_page", default=20, type=int)), 100)
    search = (request.args.get("search") or "").strip()
    status_filter = (request.args.get("status") or "all").strip().lower()
    subscription_filter = (request.args.get("subscription") or "all").strip().lower()
    onboarding_filter = (request.args.get("onboarding") or "all").strip().lower()
    hide_test_raw = request.args.get("hide_test_accounts", "true").strip().lower()
    hide_test_accounts = hide_test_raw not in ("false", "0", "no")

    query = UserProfile.query.filter(UserProfile.role == "user")

    if hide_test_accounts:
        query = query.filter(UserProfile.is_test_account.is_(False))

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(UserProfile.email.ilike(like), UserProfile.full_name.ilike(like))
        )

    if status_filter in USER_STATUSES:
        query = query.filter(UserProfile.status == status_filter)

    if onboarding_filter == "complete":
        query = query.filter(UserProfile.onboarding_completed.is_(True))
    elif onboarding_filter == "pending":
        query = query.filter(UserProfile.onboarding_completed.is_(False))

    if subscription_filter == "free":
        from app.models.subscription_model import Subscription

        query = query.outerjoin(Subscription, Subscription.profile_id == UserProfile.id).filter(
            or_(Subscription.id.is_(None), Subscription.plan == "free")
        )
    elif subscription_filter == "premium":
        from app.models.subscription_model import Subscription

        query = query.join(Subscription, Subscription.profile_id == UserProfile.id).filter(
            Subscription.plan == "premium",
            Subscription.status == "active",
        )

    pagination = query.order_by(UserProfile.registration_date.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return jsonify(
        {
            "users": [user_list_dict(user) for user in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }
    ), 200


def get_user(user_id: int):
    user = get_target_user(user_id)
    if not user:
        return error_response("admin.user_not_found", "User not found.", 404)

    log_admin_action(current_user.id, "view", target_user_id=user.id)
    err = _commit_or_error("view")
    if err:
        return err

    sub = user.subscription
    return jsonify(
        {
            "user": user_detail_dict(user),
            "subscription": {
                "plan": sub.plan if sub else "free",
                "status": sub.status if sub else "active",
                "label": subscription_label(user),
                "current_period_end": (
                    sub.current_period_end.isoformat()
                    if sub and sub.current_period_end
                    else None
                ),
                "created_at": sub.created_at.isoformat() if sub and sub.created_at else None,
            },
            "payment_history": {
                "implemented": False,
                "message": "PayHere payment history is not implemented yet.",
                "records": [],
            },
            "activity": {
                "last_active_at": (
                    user.last_active_at.isoformat() if user.last_active_at else None
                ),
                "login_count": user.login_count,
                "onboarding_completed": user.onboarding_completed,
            },
            "consents": consent_rows(user.id),
            "admin_action_logs": action_log_rows(user.id),
        }
    ), 200


def toggle_suspend(user_id: int):
    user = get_target_user(user_id)
    if not user:
        return error_response("admin.user_not_found", "User not found.", 404)

    if user.status == "banned":
        return validation_errors(
            [("admin.user_banned", "Banned users must be unbanned from the detail page.")],
            400,
        )

    if user.status == "active":
        user.status = "suspended"
        action_type = "suspend"
        notes = "Account suspended"
    else:
        user.status = "active"
        action_type = "unsuspend"
        notes = "Account reactivated"

    log_admin_action(current_user.id, action_type, target_user_id=user.id, notes=notes)
    err = _commit_or_error(action_type)
    if err:
        return err

    return jsonify({"message": "User status updated.", "user": user_detail_dict(user)}), 200


def update_status(user_id: int):
    user = get_target_user(user_id)
    if not user:
        return error_response("admin.user_not_found", "User not found.", 404)

    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    if status not in USER_STATUSES:
        return validation_errors(
            [("validation.status_invalid", "status must be active, suspended, or banned.")],
            400,
        )

    previous = user.status
    user.status = status
    log_admin_action(
        current_user.id,
        "update_status",
        target_user_id=user.id,
        notes=f"{previous} -> {status}",
    )
    err = _commit_or_error("update_status")
    if err:
        return err

    return jsonify({"message": "User status updated.", "user": user_detail_dict(user)}), 200


def force_logout(user_id: int):
    user = get_target_user(user_id)
    if not user:
        return error_response("admin.user_not_found", "User not found.", 404)

    user.token_valid_after = utc_now()
    log_admin_action(
        current_user.id,
        "force_logout",
        target_user_id=user.id,
        notes="All sessions invalidated via token_valid_after",
    )
    err = _commit_or_error("force_logout")
    if err:
        return err

    return jsonify({"message": "All active sessions have been invalidated."}), 200


def request_delete(user_id: int):
    user = get_target_user(user_id)
    if not user:
        return error_response("admin.user_not_found", "User not found.", 404)

    privacy_request = create_privacy_request(user, "delete")
    log_admin_action(
        current_user.id,
        "request_delete",
        target_user_id=user.id,
        notes=f"PrivacyRequest id={privacy_request.id}",
    )
    err = _commit_or_error("request_delete")
    if err:
        return err

    return jsonify(
        {
            "message": "Deletion request created. Complete it from Privacy & Compliance.",
            "privacy_request_id": privacy_request.id,
            "redirect_path": "/admin/privacy",
        }
    ), 201


def toggle_test_account(user_id: int):
    user = get_target_user(user_id)
    if not user:
        return error_response("admin.user_not_found", "User not found.", 404)

    data = request.get_json(silent=True) or {}
    if "is_test_account" in data:
        user.is_test_account = bool(data["is_test_account"])
    else:
        user.is_test_account = not user.is_test_account

    action_type = "mark_test_account" if user.is_test_account else "unmark_test_account"
    log_admin_action(current_user.id, action_type, target_user_id=user.id)
    err = _commit_or_error(action_type)
    if err:
        return err

    return jsonify({"message": "Test account flag updated.", "user": user_detail_dict(user)}), 200


def bulk_export():
    data = request.get_json(silent=True) or {}
    user_ids = data.get("user_ids") or []
    if not isinstance(user_ids, list) or not user_ids:
        return validation_errors(
            [("validation.user_ids_required", "user_ids must be a non-empty array.")],
            400,
        )

    try:
        ids = [int(uid) for uid in user_ids]
    except (TypeError, ValueError):
        return validation_errors(
            [("validation.user_ids_invalid", "user_ids must contain integers.")],
            400,
        )

    users = (
        UserProfile.query.filter(
            UserProfile.id.in_(ids),
            UserProfile.role == "user",
        )
        .order_by(UserProfile.id.asc())
        .all()
    )

    log_admin_action(
        current_user.id,
        "bulk_export",
        notes=f"Exported {len(users)} users: {ids}",
    )
    err = _commit_or_error("bulk_export")
    if err:
        return err

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "full_name", "email", "status", "subscription"])
    for user in users:
        writer.writerow([
            user.id,
            user.full_name,
            user.email,
            user.status,
            subscription_label(user),
        ])

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = 'attachment; filename="penmozhi-selected-users.csv"'
    return response


def test_account_candidates():
    return jsonify({"candidates": find_test_account_candidates()}), 200
