from datetime import date, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.daily_log_model import DailyLog
from app.models.educational_resource_model import EducationalResource
from app.models.forum_post_model import ForumPost
from app.models.health_profile_model import HealthProfile
from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.models.user_profile_model import UserProfile


def _date_series(days: int):
    today = date.today()
    return [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def _counts_by_day(model, date_column, since_date):
    rows = (
        db.session.query(func.date(date_column).label("day"), func.count(model.id))
        .filter(date_column >= since_date)
        .group_by(func.date(date_column))
        .all()
    )
    return {str(row.day): row[1] for row in rows}


def get_platform_analytics(days: int = 30):
    days = max(7, min(int(days or 30), 90))
    since = date.today() - timedelta(days=days - 1)
    since_dt = since

    total_users = UserProfile.query.filter_by(role="user").count()
    total_admins = UserProfile.query.filter_by(role="admin").count()
    onboarding_completed = (
        UserProfile.query.filter_by(role="user", onboarding_completed=True).count()
    )

    english_users = UserProfile.query.filter_by(role="user", language_preference="english").count()
    tamil_users = UserProfile.query.filter_by(role="user", language_preference="tamil").count()

    totals = {
        "cycles": CycleHistoryLog.query.count(),
        "symptoms": SymptomTrackingLog.query.count(),
        "daily_logs": DailyLog.query.count(),
        "forum_posts": ForumPost.query.count(),
        "reminders": MedicationSupplementReminder.query.count(),
        "education_articles": EducationalResource.query.count(),
    }

    pcos_users = 0
    for profile in HealthProfile.query.filter(HealthProfile.health_conditions.isnot(None)).all():
        conditions = profile.health_conditions or []
        if isinstance(conditions, list) and "pcos" in conditions:
            pcos_users += 1

    registration_counts = _counts_by_day(
        UserProfile,
        UserProfile.registration_date,
        since_dt,
    )
    cycle_counts = _counts_by_day(CycleHistoryLog, CycleHistoryLog.created_at, since_dt)
    symptom_counts = _counts_by_day(
        SymptomTrackingLog,
        SymptomTrackingLog.date_time,
        since_dt,
    )
    daily_log_counts = {
        str(row.log_date): row[1]
        for row in db.session.query(DailyLog.log_date, func.count(DailyLog.id))
        .filter(DailyLog.log_date >= since)
        .group_by(DailyLog.log_date)
        .all()
    }

    registration_trend = []
    activity_trend = []
    for day in _date_series(days):
        day_key = day.isoformat()
        registration_trend.append(
            {
                "date": day_key,
                "registrations": registration_counts.get(day_key, 0),
            }
        )
        activity_trend.append(
            {
                "date": day_key,
                "cycles": cycle_counts.get(day_key, 0),
                "symptoms": symptom_counts.get(day_key, 0),
                "daily_logs": daily_log_counts.get(day_key, 0),
            }
        )

    recent_active_users = (
        db.session.query(func.count(func.distinct(SymptomTrackingLog.profile_id)))
        .filter(SymptomTrackingLog.date_time >= since_dt)
        .scalar()
        or 0
    )

    return {
        "days": days,
        "summary": {
            "total_users": total_users,
            "total_admins": total_admins,
            "onboarding_completed": onboarding_completed,
            "onboarding_rate": round((onboarding_completed / total_users) * 100, 1)
            if total_users
            else 0,
            "english_users": english_users,
            "tamil_users": tamil_users,
            "pcos_users": int(pcos_users or 0),
            "recent_active_users": int(recent_active_users),
            **totals,
        },
        "registration_trend": registration_trend,
        "activity_trend": activity_trend,
    }
