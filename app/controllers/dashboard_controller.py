from datetime import date

from flask import jsonify
from flask_jwt_extended import current_user

from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.services.cycle_prediction_service import compute_cycle_insights

PHASE_TIP_KEYS = {
    "menstrual": "dashboard.tips.menstrual",
    "follicular": "dashboard.tips.follicular",
    "fertile": "dashboard.tips.fertile",
    "ovulation": "dashboard.tips.ovulation",
    "luteal": "dashboard.tips.luteal",
    "pms": "dashboard.tips.pms",
}


def _symptoms_for_today(profile_id):
    today = date.today()
    logs = (
        SymptomTrackingLog.query.filter_by(profile_id=profile_id)
        .order_by(SymptomTrackingLog.date_time.desc())
        .all()
    )
    today_logs = [
        log
        for log in logs
        if log.date_time and log.date_time.date() == today
    ]
    return [log.to_dict() for log in today_logs]


def _upcoming_reminders(profile_id, limit=3):
    reminders = (
        MedicationSupplementReminder.query.filter_by(profile_id=profile_id)
        .order_by(MedicationSupplementReminder.scheduled_time.asc())
        .limit(limit)
        .all()
    )
    return [reminder.to_dict() for reminder in reminders]


def get_summary():
    user = current_user
    insights = compute_cycle_insights(user)
    health = user.health_profile

    phase = insights.get("current_phase")
    tip_key = PHASE_TIP_KEYS.get(phase, "dashboard.tips.default")

    return jsonify(
        {
            "cycle_insights": insights,
            "today_symptoms": _symptoms_for_today(user.id),
            "upcoming_reminders": _upcoming_reminders(user.id),
            "health_tip_key": tip_key,
            "water_intake_goal_liters": health.water_intake_liters if health else 2.0,
            "quick_actions": [
                {"href": "/dashboard/cycle", "label_key": "dashboard.actions.logPeriod"},
                {"href": "/dashboard/daily-log", "label_key": "dashboard.actions.dailyLog"},
                {"href": "/dashboard/insights", "label_key": "dashboard.actions.viewInsights"},
                {"href": "/dashboard/symptoms", "label_key": "dashboard.actions.logSymptom"},
                {"href": "/dashboard/reminders", "label_key": "dashboard.actions.viewReminders"},
            ],
        }
    ), 200
