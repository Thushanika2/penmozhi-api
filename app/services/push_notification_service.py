import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app
from pywebpush import WebPushException, webpush

from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.models.push_subscription_model import PushSubscription
from app.models.user_profile_model import UserProfile
from app.services.cycle_prediction_service import compute_cycle_insights

logger = logging.getLogger(__name__)


def _is_expired_subscription(error: WebPushException) -> bool:
    response = getattr(error, "response", None)
    return response is not None and response.status_code in (404, 410)


def _send_web_push(subscription: PushSubscription, payload: dict) -> bool:
    private_key = current_app.config.get("VAPID_PRIVATE_KEY")
    claims_email = current_app.config.get("VAPID_CLAIMS_EMAIL")
    if not private_key or not claims_email:
        logger.warning("VAPID configuration is incomplete; push was not sent.")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=private_key,
            vapid_claims={"sub": claims_email},
            timeout=10,
        )
        return True
    except WebPushException as error:
        if _is_expired_subscription(error):
            logger.info("Removing expired push subscription %s.", subscription.id)
            db.session.delete(subscription)
        else:
            logger.warning("Web push failed for subscription %s: %s", subscription.id, error)
        return False
    except Exception:
        logger.exception("Unexpected web push failure for subscription %s.", subscription.id)
        return False


def _notify_user(user: UserProfile, payload: dict) -> bool:
    subscriptions = PushSubscription.query.filter_by(profile_id=user.id).all()
    sent = False
    for subscription in subscriptions:
        sent = _send_web_push(subscription, payload) or sent
    db.session.flush()
    return sent


def _local_now(user: UserProfile, now_utc: datetime) -> datetime:
    try:
        timezone = ZoneInfo(user.timezone or "Asia/Colombo")
    except ZoneInfoNotFoundError:
        logger.warning("Invalid timezone %r for user %s; using Asia/Colombo.", user.timezone, user.id)
        timezone = ZoneInfo("Asia/Colombo")
    return now_utc.astimezone(timezone)


def _send_due_reminders(user: UserProfile, local_now: datetime) -> None:
    health = HealthProfile.query.filter_by(profile_id=user.id).first()
    if not health or not health.notify_medication:
        return

    today = local_now.date()
    for reminder in MedicationSupplementReminder.query.filter_by(profile_id=user.id).all():
        # These reminders have no date in the data model, so they recur every day.
        if reminder.adherence_date != today and reminder.adherence_status != "pending":
            reminder.adherence_status = "pending"
            reminder.adherence_date = None

        scheduled = reminder.scheduled_time
        if (
            not scheduled
            or reminder.adherence_status == "taken"
            or reminder.last_push_sent_on == today
            or (scheduled.hour, scheduled.minute) != (local_now.hour, local_now.minute)
        ):
            continue

        body_parts = [part for part in (reminder.dosage, reminder.reminder_type.title()) if part]
        sent = _notify_user(
            user,
            {
                "title": f"Reminder: {reminder.item_name}",
                "body": " - ".join(body_parts) or f"Time to take {reminder.item_name}.",
                "reminder_id": reminder.id,
                "url": "/dashboard/reminders",
            },
        )
        if sent:
            reminder.last_push_sent_on = today


def _send_cycle_notifications(user: UserProfile, today: date) -> None:
    health = HealthProfile.query.filter_by(profile_id=user.id).first()
    if not health or health.last_notified_for == today:
        return
    insights = compute_cycle_insights(user, today)
    if not insights.get("has_data"):
        return

    sent = False
    if health.notify_period and insights.get("next_period_date"):
        days_until = (date.fromisoformat(insights["next_period_date"]) - today).days
        if days_until in (0, 1, 3):
            sent |= _notify_user(user, {
                "title": "Period approaching",
                "body": f"Your next period is expected in {days_until} day(s).",
                "url": "/dashboard/cycle",
            })
    if health.notify_ovulation and insights.get("ovulation_date"):
        days_until = (date.fromisoformat(insights["ovulation_date"]) - today).days
        if days_until in (0, 1):
            sent |= _notify_user(user, {
                "title": "Ovulation window",
                "body": "You may be entering your fertile window soon.",
                "url": "/dashboard/cycle",
            })
    if sent:
        health.last_notified_for = today


def run_scheduled_notifications(now_utc: datetime | None = None):
    """Dispatch due daily reminders once per user's local calendar day."""
    now_utc = now_utc or datetime.now(ZoneInfo("UTC"))
    for user in UserProfile.query.filter_by(role="user", status="active").all():
        local_now = _local_now(user, now_utc)
        _send_due_reminders(user, local_now)
        _send_cycle_notifications(user, local_now.date())
    db.session.commit()
