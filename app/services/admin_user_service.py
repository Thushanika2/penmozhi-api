"""Admin user management helpers."""

from __future__ import annotations

from app.extensions import db
from app.models.admin_action_log_model import AdminActionLog
from app.models.user_consent_model import UserConsent
from app.models.user_profile_model import UserProfile
from app.utils import utc_now

USER_STATUSES = ("active", "suspended", "banned")

TEST_EMAIL_PATTERNS = (
    "gemini-test-%@example.com",
    "test+%@example.com",
    "+%test%@example.com",
)


def log_admin_action(
    admin_id: int,
    action_type: str,
    *,
    target_user_id: int | None = None,
    notes: str | None = None,
) -> AdminActionLog:
    entry = AdminActionLog(
        admin_id=admin_id,
        action_type=action_type,
        target_user_id=target_user_id,
        notes=notes,
    )
    db.session.add(entry)
    return entry


def subscription_label(user: UserProfile) -> str:
    sub = user.subscription
    if not sub or sub.plan == "free":
        return "free"

    now = utc_now()
    period_end = sub.current_period_end
    if period_end and period_end < now:
        return "expired"

    if sub.status == "trialing" or sub.plan == "trial":
        return "trial"

    if sub.plan == "premium" and sub.status == "active":
        return "premium"

    if sub.status in {"canceled", "expired", "past_due"}:
        return "expired"

    return "free"


def user_list_dict(user: UserProfile) -> dict:
    data = user.to_dict()
    data["subscription"] = subscription_label(user)
    return data


def user_detail_dict(user: UserProfile) -> dict:
    return user_list_dict(user)


def get_target_user(user_id: int) -> UserProfile | None:
    return UserProfile.query.filter_by(id=user_id, role="user").first()


def consent_rows(user_id: int) -> list[dict]:
    consents = (
        UserConsent.query.filter_by(user_id=user_id)
        .order_by(UserConsent.granted_at.desc())
        .all()
    )
    return [
        {
            "id": consent.id,
            "user_id": consent.user_id,
            "consent_type": consent.consent_type,
            "policy_version": consent.policy_version,
            "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
            "context": consent.context,
        }
        for consent in consents
    ]


def action_log_rows(user_id: int, *, limit: int = 50) -> list[dict]:
    logs = (
        AdminActionLog.query.filter_by(target_user_id=user_id)
        .order_by(AdminActionLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [entry.to_dict() for entry in logs]


def find_test_account_candidates() -> list[dict]:
    from sqlalchemy import or_

    filters = []
    for pattern in TEST_EMAIL_PATTERNS:
        filters.append(UserProfile.email.ilike(pattern.replace("%", "%")))

    # Explicit patterns
    explicit = [
        UserProfile.email.ilike("gemini-test-%@example.com"),
        UserProfile.email.ilike("%@example.com"),
        UserProfile.email.ilike("test%@%"),
    ]

    users = (
        UserProfile.query.filter(
            UserProfile.role == "user",
            or_(*explicit),
        )
        .order_by(UserProfile.email.asc())
        .all()
    )

    # Narrow example.com to likely test accounts
    candidates = []
    for user in users:
        email = user.email.lower()
        is_candidate = (
            email.startswith("gemini-test-")
            or email.endswith("@example.com")
            or email.startswith("test")
            or "+test" in email
        )
        if is_candidate:
            candidates.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_test_account": user.is_test_account,
                "registration_date": (
                    user.registration_date.isoformat() if user.registration_date else None
                ),
            })
    return candidates
