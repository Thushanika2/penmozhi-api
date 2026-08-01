from datetime import date, timedelta

from app.services.cycle_prediction_service import (
    clamp_cycle_length,
    compute_phase_schedule,
    estimate_cycle_length,
)


def _period_start_dates(user):
    """Collect period start dates from cycle history only."""
    cycles = list(user.cycle_history_logs or [])
    if not cycles:
        health = user.health_profile
        if health and health.last_period_start:
            return [health.last_period_start]
        return []

    return sorted({c.cycle_start_date for c in cycles if c.cycle_start_date})


def compute_conceive_insights(user, reference_date=None):
    """
    Fertile window and ovulation predictions from period start dates only.
    Reuses compute_phase_schedule() for phase math.
    """
    reference_date = reference_date or date.today()
    starts = _period_start_dates(user)

    health = user.health_profile
    default_cycle = health.average_cycle_length if health and health.average_cycle_length else 28
    default_cycle = clamp_cycle_length(default_cycle)
    default_period = health.average_period_length if health and health.average_period_length else 5

    if not starts:
        return {
            "has_data": False,
            "fertile_window_start": None,
            "fertile_window_end": None,
            "ovulation_date": None,
            "next_period_date": None,
            "average_cycle_length": default_cycle,
        }

    last_start = max(starts)
    avg_cycle, _meta = estimate_cycle_length(starts, default_cycle)

    schedule = compute_phase_schedule(avg_cycle, default_period)
    ovulation_peak_day = schedule["ovulation_peak_day"]
    ovulation_start_day = schedule["ovulation"]["start_day"]
    ovulation_end_day = schedule["ovulation"]["end_day"]

    current_start = last_start
    next_period = current_start + timedelta(days=avg_cycle)
    while next_period <= reference_date:
        current_start = next_period
        next_period = current_start + timedelta(days=avg_cycle)

    ovulation_date = current_start + timedelta(days=ovulation_peak_day - 1)
    fertile_start = current_start + timedelta(days=ovulation_start_day - 1)
    fertile_end = current_start + timedelta(days=ovulation_end_day - 1)

    return {
        "has_data": True,
        "last_period_start": current_start.isoformat(),
        "fertile_window_start": fertile_start.isoformat(),
        "fertile_window_end": fertile_end.isoformat(),
        "ovulation_date": ovulation_date.isoformat(),
        "next_period_date": next_period.isoformat(),
        "average_cycle_length": avg_cycle,
        "phase_schedule": schedule,
    }
