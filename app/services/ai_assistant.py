import logging
from datetime import date, datetime, timedelta

from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.models.user_profile_model import UserProfile
from app.services.cycle_prediction_service import compute_cycle_insights

logger = logging.getLogger(__name__)

_PHASE_LABELS = {
    "menstrual": "Menstrual",
    "follicular": "Follicular",
    "ovulation": "Ovulation",
    "fertile": "Ovulation (fertile window)",
    "luteal": "Luteal",
    "pms": "Luteal (PMS window)",
}


def _format_phase(phase: str | None) -> str | None:
    if not phase:
        return None
    return _PHASE_LABELS.get(phase, phase.replace("_", " ").title())


def _calculate_age(date_of_birth: date | None) -> int | None:
    if not date_of_birth:
        return None
    today = date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


def _format_symptom_summary(symptoms: list[SymptomTrackingLog]) -> str | None:
    if not symptoms:
        return None

    parts = []
    for symptom in symptoms[:3]:
        days_ago = (date.today() - symptom.date_time.date()).days
        label = symptom.category
        if symptom.pain_severity >= 4:
            label = f"{label} (pain {symptom.pain_severity}/10)"
        if symptom.mood_status:
            label = f"{label}, mood: {symptom.mood_status}"
        when = "today" if days_ago == 0 else f"{days_ago} days ago"
        parts.append(f"{label} ({when})")

    return "; ".join(parts)


def _latest_pcos_status(health: HealthProfile | None) -> PCOSDisorderStatus | None:
    if not health:
        return None
    return (
        PCOSDisorderStatus.query.filter_by(health_profile_id=health.id)
        .order_by(PCOSDisorderStatus.created_at.desc())
        .first()
    )


def _format_pcos_status(pcos: PCOSDisorderStatus | None) -> str | None:
    if not pcos:
        return None
    if pcos.diagnosis_status and pcos.diagnosis_status != "not_diagnosed":
        return f"{pcos.diagnosis_status.replace('_', ' ')} ({pcos.disorder_type})"
    if pcos.disorder_type and pcos.disorder_type != "none":
        return pcos.disorder_type.replace("_", " ")
    return None


def build_user_context(user_id: int) -> str:
    """
    Build a short plain-text summary of the user's health data for AI personalization.
    Returns an empty string if context building fails; never raises.
    """
    try:
        user = UserProfile.query.filter_by(id=user_id).first()
        if not user:
            return "No cycle data logged yet."

        health = HealthProfile.query.filter_by(profile_id=user_id).first()
        insights = compute_cycle_insights(user)

        lines: list[str] = []

        age = _calculate_age(user.date_of_birth)
        if age is not None:
            lines.append(f"Age: {age}")

        if insights.get("has_data"):
            avg_cycle = insights.get("average_cycle_length")
            avg_period = insights.get("average_period_length")
            if avg_cycle:
                lines.append(f"Average cycle length: {avg_cycle} days")
            if avg_period:
                lines.append(f"Average period length: {avg_period} days")

            last_start_raw = insights.get("last_period_start")
            if last_start_raw:
                last_start = date.fromisoformat(last_start_raw)
                days_since = (date.today() - last_start).days
                lines.append(f"Last period started: {days_since} days ago")

            phase_label = _format_phase(insights.get("current_phase"))
            if phase_label:
                lines.append(f"Estimated phase: {phase_label}")
        elif health:
            if health.average_cycle_length:
                lines.append(f"Average cycle length: {health.average_cycle_length} days")
            if health.average_period_length:
                lines.append(f"Average period length: {health.average_period_length} days")
            if health.last_period_start:
                days_since = (date.today() - health.last_period_start).days
                lines.append(f"Last period started: {days_since} days ago")

        cutoff = datetime.utcnow() - timedelta(days=7)
        recent_symptoms = (
            SymptomTrackingLog.query.filter_by(profile_id=user_id)
            .filter(SymptomTrackingLog.date_time >= cutoff)
            .order_by(SymptomTrackingLog.date_time.desc())
            .limit(5)
            .all()
        )
        symptom_summary = _format_symptom_summary(recent_symptoms)
        if symptom_summary:
            lines.append(f"Recent symptoms logged: {symptom_summary}")

        pcos_summary = _format_pcos_status(_latest_pcos_status(health))
        if pcos_summary:
            lines.append(f"PCOS status: {pcos_summary}")

        if not lines:
            return "No cycle data logged yet."

        return "\n".join(lines[:5])
    except Exception:
        logger.warning("Failed to build AI user context for profile_id=%s", user_id)
        return ""
