import logging
from datetime import date, datetime, time

from flask import current_app

from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.models.push_subscription_model import PushSubscription
from app.models.user_profile_model import UserProfile
from app.services.cycle_prediction_service import compute_cycle_insights
from app.utils import utc_now

logger = logging.getLogger(__name__)


def _send_web_push(subscription: PushSubscription, title: str, body: str):
    """Send a web push notification via pywebpush."""
    vapid_private = current_app.config.get("VAPID_PRIVATE_KEY")
    vapid_claims = {"sub": current_app.config.get("VAPID_CLAIMS_EMAIL", "mailto:admin@penmozhi.com")}

    if not vapid_private:
        logger.debug("VAPID_PRIVATE_KEY not configured; skipping push.")
        return False

    try:
        from pywebpush import webpush, WebPushException
        import json

        payload = json.dumps({"title": title, "body": body})
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=vapid_private,
            vapid_claims=vapid_claims,
        )
        return True
    except Exception:
        logger.exception("Failed to send web push to subscription %s", subscription.id)
        return False


def _notify_user(user: UserProfile, title: str, body: str):
    subs = PushSubscription.query.filter_by(profile_id=user.id).all()
    for sub in subs:
        _send_web_push(sub, title, body)


def run_scheduled_notifications():
    """Check reminders and cycle predictions; send push notifications."""
    today = date.today()
    now = utc_now()
    current_time = now.time()

    users = UserProfile.query.filter_by(role="user").all()
    for user in users:
        health = HealthProfile.query.filter_by(profile_id=user.id).first()
        if not health:
            continue

        if health.notify_medication:
            reminders = MedicationSupplementReminder.query.filter_by(profile_id=user.id).all()
            for reminder in reminders:
                if reminder.adherence_status == "taken":
                    continue
                scheduled = reminder.scheduled_time
                if scheduled and abs(
                    (datetime.combine(today, scheduled) - datetime.combine(today, current_time)).total_seconds()
                ) < 300:
                    _notify_user(
                        user,
                        "Medication reminder",
                        f"Time to take {reminder.item_name}.",
                    )

        insights = compute_cycle_insights(user, today)
        if not insights.get("has_data"):
            continue

        if health.last_notified_for == today:
            continue

        sent = False
        if health.notify_period and insights.get("next_period_date"):
            next_period = date.fromisoformat(insights["next_period_date"])
            days_until = (next_period - today).days
            if days_until in (0, 1, 3):
                _notify_user(
                    user,
                    "Period approaching",
                    f"Your next period is expected in {days_until} day(s).",
                )
                sent = True

        if health.notify_ovulation and insights.get("ovulation_date"):
            ovulation = date.fromisoformat(insights["ovulation_date"])
            days_until_ov = (ovulation - today).days
            if days_until_ov in (0, 1):
                _notify_user(
                    user,
                    "Ovulation window",
                    "You may be entering your fertile window soon.",
                )
                sent = True

        if sent:
            health.last_notified_for = today
            db.session.commit()
