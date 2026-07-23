from datetime import date, timedelta

PHASE_MENSTRUAL = "menstrual"
PHASE_FOLLICULAR = "follicular"
PHASE_FERTILE = "fertile"
PHASE_OVULATION = "ovulation"
PHASE_LUTEAL = "luteal"
PHASE_PMS = "pms"

# Luteal phase length is relatively stable (~14 days) in most cycles.
LUTEAL_PHASE_DAYS = 14
# Ovulation window: peak day ± 1 (3 days total), aligned with standard fertility charts.
OVULATION_WINDOW_RADIUS = 1
# PMS commonly occurs in the final ~7 days before the next period.
PMS_DAYS_BEFORE_PERIOD = 7


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
        "follicular_start_date": None,
        "follicular_end_date": None,
        "luteal_start_date": None,
        "luteal_end_date": None,
        "days_until_next_period": None,
        "average_cycle_length": 28,
        "average_period_length": 5,
        "phase_ranges": None,
        "statistics": {
            "average_cycle_length": None,
            "average_period_length": None,
            "longest_cycle": None,
            "shortest_cycle": None,
            "logged_cycles": 0,
        },
    }


def compute_phase_schedule(cycle_length: int, period_length: int) -> dict:
    """
    Map cycle days to phases using a standard gynecological model:
    - Menstruation: days 1..period_length
    - Follicular: after period until ovulation window
    - Ovulation: 3-day fertile window centred ~14 days before next period
    - Luteal: after ovulation until cycle end (PMS = last 7 days)
    """
    cycle_length = max(int(cycle_length), 21)
    period_length = min(max(int(period_length), 2), cycle_length - 10)

    ovulation_peak = cycle_length - LUTEAL_PHASE_DAYS
    ovulation_start = max(period_length + 1, ovulation_peak - OVULATION_WINDOW_RADIUS)
    ovulation_end = min(cycle_length, ovulation_peak + OVULATION_WINDOW_RADIUS)

    follicular_start = period_length + 1
    follicular_end = ovulation_start - 1

    luteal_start = ovulation_end + 1
    luteal_end = cycle_length

    pms_start = max(luteal_start, cycle_length - PMS_DAYS_BEFORE_PERIOD + 1)

    return {
        "menstrual": {"start_day": 1, "end_day": period_length},
        "follicular": (
            {"start_day": follicular_start, "end_day": follicular_end}
            if follicular_end >= follicular_start
            else None
        ),
        "ovulation": {"start_day": ovulation_start, "end_day": ovulation_end},
        "luteal": (
            {"start_day": luteal_start, "end_day": luteal_end}
            if luteal_end >= luteal_start
            else None
        ),
        "pms": {"start_day": pms_start, "end_day": cycle_length},
        "ovulation_peak_day": ovulation_peak,
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


def _detect_phase(cycle_day, schedule):
    menstrual = schedule["menstrual"]
    if menstrual["start_day"] <= cycle_day <= menstrual["end_day"]:
        return PHASE_MENSTRUAL

    follicular = schedule.get("follicular")
    if follicular and follicular["start_day"] <= cycle_day <= follicular["end_day"]:
        return PHASE_FOLLICULAR

    ovulation = schedule["ovulation"]
    if ovulation["start_day"] <= cycle_day <= ovulation["end_day"]:
        if cycle_day == schedule["ovulation_peak_day"]:
            return PHASE_OVULATION
        return PHASE_FERTILE

    pms = schedule["pms"]
    if pms["start_day"] <= cycle_day <= pms["end_day"]:
        return PHASE_PMS

    luteal = schedule.get("luteal")
    if luteal and luteal["start_day"] <= cycle_day <= luteal["end_day"]:
        return PHASE_LUTEAL

    return PHASE_LUTEAL


def _date_for_cycle_day(cycle_start: date, day: int) -> date:
    return cycle_start + timedelta(days=day - 1)


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
    schedule = compute_phase_schedule(avg_cycle, avg_period)

    ovulation_peak = schedule["ovulation_peak_day"]
    ovulation = _date_for_cycle_day(current_start, ovulation_peak)
    ovulation_start = _date_for_cycle_day(current_start, schedule["ovulation"]["start_day"])
    ovulation_end = _date_for_cycle_day(current_start, schedule["ovulation"]["end_day"])
    pms_start = _date_for_cycle_day(current_start, schedule["pms"]["start_day"])
    pms_end = next_period - timedelta(days=1)

    follicular = schedule.get("follicular")
    follicular_start = (
        _date_for_cycle_day(current_start, follicular["start_day"]) if follicular else None
    )
    follicular_end = (
        _date_for_cycle_day(current_start, follicular["end_day"]) if follicular else None
    )

    luteal = schedule.get("luteal")
    luteal_start = _date_for_cycle_day(current_start, luteal["start_day"]) if luteal else None
    luteal_end = pms_end

    cycle_day = (reference_date - current_start).days + 1
    if cycle_day < 1:
        cycle_day = 1
    if cycle_day > avg_cycle:
        cycle_day = avg_cycle

    phase = _detect_phase(cycle_day, schedule)

    return {
        "has_data": True,
        "cycle_day": cycle_day,
        "current_phase": phase,
        "last_period_start": current_start.isoformat(),
        "next_period_date": next_period.isoformat(),
        "ovulation_date": ovulation.isoformat(),
        "fertile_window_start": ovulation_start.isoformat(),
        "fertile_window_end": ovulation_end.isoformat(),
        "pms_window_start": pms_start.isoformat(),
        "pms_window_end": pms_end.isoformat(),
        "follicular_start_date": follicular_start.isoformat() if follicular_start else None,
        "follicular_end_date": follicular_end.isoformat() if follicular_end else None,
        "luteal_start_date": luteal_start.isoformat() if luteal_start else None,
        "luteal_end_date": luteal_end.isoformat() if luteal_end else None,
        "days_until_next_period": (next_period - reference_date).days,
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "phase_ranges": schedule,
        "statistics": stats,
    }
