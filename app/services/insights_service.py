from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.daily_log_model import DailyLog
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.services.cycle_prediction_service import compute_cycle_insights

PAIN_SCORE = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}
ENERGY_SCORE = {"low": 1, "medium": 2, "high": 3}


def _cutoff_date(months: int) -> date:
    return date.today() - timedelta(days=max(1, months) * 31)


def _cycle_length_trend(cycles):
    starts = sorted(c.cycle_start_date for c in cycles if c.cycle_start_date)
    trend = []
    for index in range(1, len(starts)):
        trend.append(
            {
                "start_date": starts[index].isoformat(),
                "cycle_length": (starts[index] - starts[index - 1]).days,
            }
        )
    return trend


def _period_length_trend(cycles):
    trend = []
    for cycle in cycles:
        if not cycle.cycle_start_date or not cycle.cycle_end_date:
            continue
        trend.append(
            {
                "start_date": cycle.cycle_start_date.isoformat(),
                "period_length": (cycle.cycle_end_date - cycle.cycle_start_date).days + 1,
            }
        )
    return trend


def _symptom_trends(symptoms):
    by_date = defaultdict(lambda: {"count": 0, "pain_sum": 0})
    by_category = defaultdict(lambda: {"count": 0, "pain_sum": 0})

    for symptom in symptoms:
        day = symptom.date_time.date().isoformat() if symptom.date_time else "unknown"
        by_date[day]["count"] += 1
        by_date[day]["pain_sum"] += symptom.pain_severity

        category = symptom.category or "uncategorized"
        by_category[category]["count"] += 1
        by_category[category]["pain_sum"] += symptom.pain_severity

    date_trends = [
        {
            "date": day,
            "count": stats["count"],
            "avg_pain": round(stats["pain_sum"] / stats["count"], 2),
        }
        for day, stats in sorted(by_date.items())
    ]

    category_trends = [
        {
            "category": category,
            "count": stats["count"],
            "avg_pain": round(stats["pain_sum"] / stats["count"], 2),
        }
        for category, stats in sorted(by_category.items())
    ]

    return {
        "date_trends": date_trends,
        "category_trends": category_trends,
        "total_entries": len(symptoms),
    }


def compute_health_insights(user, months=6):
    months = max(1, min(int(months or 6), 24))
    cutoff = _cutoff_date(months)
    cutoff_dt = datetime.combine(cutoff, datetime.min.time())

    cycles = (
        CycleHistoryLog.query.filter_by(profile_id=user.id)
        .order_by(CycleHistoryLog.cycle_start_date.asc())
        .all()
    )
    recent_cycles = [cycle for cycle in cycles if cycle.cycle_start_date and cycle.cycle_start_date >= cutoff]

    daily_logs = (
        DailyLog.query.filter(
            DailyLog.profile_id == user.id,
            DailyLog.log_date >= cutoff,
        )
        .order_by(DailyLog.log_date.asc())
        .all()
    )

    symptoms = (
        SymptomTrackingLog.query.filter(
            SymptomTrackingLog.profile_id == user.id,
            SymptomTrackingLog.date_time >= cutoff_dt,
        )
        .order_by(SymptomTrackingLog.date_time.asc())
        .all()
    )

    cycle_insights = compute_cycle_insights(user)
    statistics = cycle_insights.get("statistics") or {}

    daily_pain_trend = []
    sleep_trend = []
    energy_trend = []
    mood_entries = []

    for log in daily_logs:
        day = log.log_date.isoformat()
        if log.pain_level:
            daily_pain_trend.append(
                {
                    "date": day,
                    "score": PAIN_SCORE.get(log.pain_level, 0),
                    "level": log.pain_level,
                }
            )
        if log.sleep_hours is not None:
            sleep_trend.append({"date": day, "hours": round(log.sleep_hours, 1)})
        if log.energy:
            energy_trend.append(
                {
                    "date": day,
                    "score": ENERGY_SCORE.get(log.energy, 0),
                    "level": log.energy,
                }
            )
        if log.mood and log.mood.strip():
            mood_entries.append(
                {
                    "date": day,
                    "mood": log.mood.strip().lower(),
                    "source": "daily_log",
                }
            )

    for symptom in symptoms:
        day = symptom.date_time.date().isoformat() if symptom.date_time else None
        if day and symptom.mood_status and symptom.mood_status.strip():
            mood_entries.append(
                {
                    "date": day,
                    "mood": symptom.mood_status.strip().lower(),
                    "source": "symptom",
                }
            )

    mood_counter = Counter(entry["mood"] for entry in mood_entries)
    mood_frequency = [
        {"mood": mood, "count": count}
        for mood, count in mood_counter.most_common(12)
    ]

    mood_by_date = defaultdict(list)
    for entry in mood_entries:
        mood_by_date[entry["date"]].append(entry["mood"])

    mood_timeline = []
    for day, moods in sorted(mood_by_date.items()):
        primary = Counter(moods).most_common(1)[0][0]
        mood_timeline.append(
            {
                "date": day,
                "primary_mood": primary,
                "entry_count": len(moods),
            }
        )

    symptom_trends = _symptom_trends(symptoms)

    return {
        "months": months,
        "has_cycle_data": bool(cycles),
        "has_daily_log_data": bool(daily_logs),
        "has_symptom_data": bool(symptoms),
        "cycle_statistics": statistics,
        "cycle_length_trend": _cycle_length_trend(recent_cycles or cycles),
        "period_length_trend": _period_length_trend(recent_cycles or cycles),
        "symptom_trends": symptom_trends,
        "daily_pain_trend": daily_pain_trend,
        "sleep_trend": sleep_trend,
        "energy_trend": energy_trend,
        "mood_frequency": mood_frequency,
        "mood_timeline": mood_timeline,
        "total_daily_logs": len(daily_logs),
    }
