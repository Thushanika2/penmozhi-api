from datetime import date, timedelta

PHASE_MENSTRUAL = "menstrual"
PHASE_FOLLICULAR = "follicular"
PHASE_FERTILE = "fertile"
PHASE_OVULATION = "ovulation"
PHASE_LUTEAL = "luteal"
PHASE_PMS = "pms"


def _empty_insights():
    return {
        "has_data": False,
        "cycle_day": None,
        "current_phase": None,
        "last_period_start": None,
        "next_period_date": None,
        "ovulation_date": None,
        "fertile_window_start": None,
        "fertile_window_end": None,
        "pms_window_start": None,
        "pms_window_end": None,
        "days_until_next_period": None,
        "average_cycle_length": 28,
        "average_period_length": 5,
        "statistics": {
            "average_cycle_length": None,
            "average_period_length": None,
            "longest_cycle": None,
            "shortest_cycle": None,
            "logged_cycles": 0,
        },
    }


def _cycle_statistics(cycles, default_cycle, default_period):
    if not cycles:
        return {
            "average_cycle_length": default_cycle,
            "average_period_length": default_period,
            "longest_cycle": None,
            "shortest_cycle": None,
            "logged_cycles": 0,
        }

    starts = sorted(c.cycle_start_date for c in cycles)
    cycle_lengths = []
    if len(starts) >= 2:
        cycle_lengths = [(starts[i] - starts[i - 1]).days for i in range(1, len(starts))]

    period_lengths = [
        (c.cycle_end_date - c.cycle_start_date).days + 1
        for c in cycles
        if c.cycle_end_date and c.cycle_start_date
    ]

    return {
        "average_cycle_length": (
            round(sum(cycle_lengths) / len(cycle_lengths)) if cycle_lengths else default_cycle
        ),
        "average_period_length": (
            round(sum(period_lengths) / len(period_lengths)) if period_lengths else default_period
        ),
        "longest_cycle": max(cycle_lengths) if cycle_lengths else None,
        "shortest_cycle": min(cycle_lengths) if cycle_lengths else None,
        "logged_cycles": len(cycles),
    }


def _resolve_cycle_window(last_start, avg_cycle, reference_date):
    current_start = last_start
    next_period = current_start + timedelta(days=avg_cycle)
    while next_period <= reference_date:
        current_start = next_period
        next_period = current_start + timedelta(days=avg_cycle)
    return current_start, next_period


def _detect_phase(reference_date, current_start, avg_period, ovulation, fertile_start, next_period):
    period_end = current_start + timedelta(days=avg_period - 1)
    pms_start = next_period - timedelta(days=7)

    if current_start <= reference_date <= period_end:
        return PHASE_MENSTRUAL
    if reference_date == ovulation:
        return PHASE_OVULATION
    if fertile_start <= reference_date <= ovulation:
        return PHASE_FERTILE
    if pms_start <= reference_date < next_period:
        return PHASE_PMS
    if period_end < reference_date < fertile_start:
        return PHASE_FOLLICULAR
    return PHASE_LUTEAL


def compute_cycle_insights(user, reference_date=None):
    reference_date = reference_date or date.today()
    health = user.health_profile
    cycles = list(user.cycle_history_logs or [])

    latest = max(cycles, key=lambda c: c.cycle_start_date) if cycles else None
    last_start = latest.cycle_start_date if latest else None
    if not last_start and health and health.last_period_start:
        last_start = health.last_period_start

    default_cycle = health.average_cycle_length if health and health.average_cycle_length else 28
    default_period = health.average_period_length if health and health.average_period_length else 5
    stats = _cycle_statistics(cycles, default_cycle, default_period)

    avg_cycle = stats["average_cycle_length"] or default_cycle
    avg_period = stats["average_period_length"] or default_period

    if not last_start:
        payload = _empty_insights()
        payload["statistics"] = stats
        return payload

    current_start, next_period = _resolve_cycle_window(last_start, avg_cycle, reference_date)
    ovulation = next_period - timedelta(days=14)
    fertile_start = ovulation - timedelta(days=5)
    pms_start = next_period - timedelta(days=7)
    pms_end = next_period - timedelta(days=1)

    cycle_day = (reference_date - current_start).days + 1
    phase = _detect_phase(
        reference_date,
        current_start,
        avg_period,
        ovulation,
        fertile_start,
        next_period,
    )

    return {
        "has_data": True,
        "cycle_day": cycle_day,
        "current_phase": phase,
        "last_period_start": current_start.isoformat(),
        "next_period_date": next_period.isoformat(),
        "ovulation_date": ovulation.isoformat(),
        "fertile_window_start": fertile_start.isoformat(),
        "fertile_window_end": ovulation.isoformat(),
        "pms_window_start": pms_start.isoformat(),
        "pms_window_end": pms_end.isoformat(),
        "days_until_next_period": (next_period - reference_date).days,
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "statistics": stats,
    }
