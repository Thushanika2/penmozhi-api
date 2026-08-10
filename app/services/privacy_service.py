"""Privacy, consent, and user data erasure helpers."""

from __future__ import annotations

from app.extensions import db
from app.models.cycle_share_model import CycleShare
from app.models.privacy_request_model import PrivacyRequest
from app.models.user_consent_model import UserConsent
from app.models.user_profile_model import UserProfile
from app.utils import utc_now

# Current policy document versions — bump when legal text changes.
POLICY_VERSIONS = {
    "terms_of_service": "1.0",
    "privacy_policy": "1.0",
    "health_data_processing": "1.0",
    "wearable_data_sharing": "1.0",
    "cycle_date_sharing": "1.0",
}

SIGNUP_CONSENT_TYPES = (
    "terms_of_service",
    "privacy_policy",
    "health_data_processing",
)

# Tables removed when a user account is hard-deleted (via SQLAlchemy cascades on UserProfile):
# forum_comments, forum_posts, symptom_tracking_logs, custom_tags, perimenopause_logs,
# pregnancy_profiles, push_subscriptions, cycle_shares (owned), wearable_connections,
# subscriptions, ai_health_assistant_sessions, medication_supplement_reminders, daily_logs,
# cycle_history_logs, password_reset_tokens, pcos_disorder_statuses (via health_profile),
# health_profiles, user_consents, privacy_requests (user_id SET NULL on completed delete).
USER_DATA_TABLES = (
    "forum_comments",
    "forum_posts",
    "symptom_tracking_logs",
    "custom_tags",
    "perimenopause_logs",
    "pregnancy_profiles",
    "push_subscriptions",
    "cycle_shares",
    "sharing_invites",
    "shared_connections",
    "wearable_connections",
    "subscriptions",
    "ai_health_assistant_sessions",
    "medication_supplement_reminders",
    "daily_logs",
    "cycle_history_logs",
    "password_reset_tokens",
    "pcos_disorder_statuses",
    "health_profiles",
    "user_consents",
    "user_profiles",
)

INTEGRATION_CATALOG = (
    {
        "provider": "oura",
        "integration_type": "wearable",
        "data_categories": ["sleep duration", "heart rate", "activity levels", "readiness scores"],
    },
    {
        "provider": "whoop",
        "integration_type": "wearable",
        "data_categories": ["strain", "recovery", "sleep performance", "heart rate variability"],
    },
    {
        "provider": "fitbit",
        "integration_type": "wearable",
        "data_categories": ["steps", "sleep", "heart rate", "activity"],
    },
    {
        "provider": "withings",
        "integration_type": "wearable",
        "data_categories": ["weight", "sleep", "heart rate", "activity"],
    },
    {
        "provider": "garmin",
        "integration_type": "wearable",
        "data_categories": ["activity", "sleep", "heart rate", "stress"],
    },
    {
        "provider": "apple",
        "integration_type": "wearable",
        "data_categories": ["activity", "sleep", "heart rate", "cycle data (HealthKit)"],
    },
    {
        "provider": "web_push",
        "integration_type": "notifications",
        "data_categories": ["device push tokens", "notification delivery metadata"],
    },
    {
        "provider": "google_gemini",
        "integration_type": "ai_processing",
        "data_categories": [
            "anonymized health context snippets",
            "AI assistant chat messages",
        ],
    },
    {
        "provider": "anthropic",
        "integration_type": "ai_processing",
        "data_categories": [
            "anonymized health context snippets",
            "AI assistant chat messages",
        ],
    },
)


def record_consent(user_id: int, consent_type: str, *, context: str | None = None) -> UserConsent:
    version = POLICY_VERSIONS.get(consent_type, "1.0")
    consent = UserConsent(
        user_id=user_id,
        consent_type=consent_type,
        policy_version=version,
        context=context,
    )
    db.session.add(consent)
    return consent


def record_signup_consents(user_id: int) -> None:
    for consent_type in SIGNUP_CONSENT_TYPES:
        record_consent(user_id, consent_type)


def record_wearable_consent(user_id: int, provider: str) -> None:
    record_consent(user_id, "wearable_data_sharing", context=provider)


def create_privacy_request(user: UserProfile, request_type: str) -> PrivacyRequest:
    if request_type not in {"export", "delete"}:
        raise ValueError("Invalid request_type")

    existing = (
        PrivacyRequest.query.filter_by(
            user_id=user.id,
            request_type=request_type,
            status="pending",
        ).first()
    )
    if existing:
        return existing

    request_row = PrivacyRequest(
        user_id=user.id,
        user_email=user.email,
        request_type=request_type,
        status="pending",
    )
    db.session.add(request_row)
    return request_row


def delete_user_account(user_id: int) -> None:
    """Hard-delete a user and all ORM-cascaded health data (not anonymization)."""
    user = db.session.get(UserProfile, user_id)
    if not user:
        return

    if user.role == "admin":
        raise ValueError("Admin accounts cannot be deleted via privacy workflow.")

    CycleShare.query.filter_by(shared_with_profile_id=user.id).update(
        {"shared_with_profile_id": None},
        synchronize_session=False,
    )
    db.session.delete(user)


def complete_privacy_request(request_row: PrivacyRequest, admin_id: int) -> None:
    if request_row.status == "completed":
        raise ValueError("Request is already completed.")

    request_row.status = "processing"
    db.session.flush()

    if request_row.request_type == "delete":
        if request_row.user_id:
            delete_user_account(request_row.user_id)
            request_row.user_id = None

    request_row.status = "completed"
    request_row.completed_at = utc_now()
    request_row.completed_by_admin_id = admin_id
