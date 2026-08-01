from datetime import date, timedelta
from statistics import median

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

# Typical menstrual cycle bounds used for prediction (WHO / ACOG common range).
MIN_CYCLE_LENGTH = 21
MAX_TYPICAL_CYCLE_LENGTH = 45
# Gaps longer than this are treated as outliers (missed logs, medication, illness, etc.).
UNUSUAL_GAP_DAYS = MAX_TYPICAL_CYCLE_LENGTH + 1
# Prefer recent typical cycles when estimating length.
RECENT_TYPICAL_WINDOW = 6

GAP_REASON_CHOICES = frozenset(
    {
        "medication",
        "medical",
        "stress",
        "missed_logging",
        "contraception",
        "pregnancy_postpartum",
        "other",
    }
)


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
        "prediction_quality": None,
        "statistics": {
            "average_cycle_length": None,
            "average_period_length": None,
            "longest_cycle": None,
            "shortest_cycle": None,
            "logged_cycles": 0,
            "typical_cycles_used": 0,
            "outlier_gaps_excluded": 0,
        },
    }


def clamp_cycle_length(length: int, default: int = 28) -> int:
    """Clamp a cycle length into the typical prediction range."""
    try:
        value = int(length)
    except (TypeError, ValueError):
        value = int(default)
    return max(MIN_CYCLE_LENGTH, min(value, MAX_TYPICAL_CYCLE_LENGTH))


def is_unusual_gap(gap_days: int) -> bool:
    return gap_days is not None and gap_days >= UNUSUAL_GAP_DAYS


def cycle_gaps_from_starts(starts):
    """Return consecutive start-to-start gaps in days for sorted start dates."""
    ordered = sorted(starts)
    return [(ordered[i] - ordered[i - 1]).days for i in range(1, len(ordered))]


def filter_typical_lengths(lengths):
    return [
        length
        for length in lengths
        if MIN_CYCLE_LENGTH <= length <= MAX_TYPICAL_CYCLE_LENGTH
    ]


def estimate_cycle_length(starts, default_cycle=28):
    """
    Estimate cycle length for predictions.

    - Uses only typical gaps (21–45 days); unusual gaps are excluded as outliers.
    - Prefers the median of the most recent typical gaps (more robust than mean).
    - Falls back to the profile/default length when no typical gaps exist.
    """
    fallback = clamp_cycle_length(default_cycle)
    ordered = sorted(starts) if starts else []
    if len(ordered) < 2:
        return fallback, {
            "typical_cycles_used": 0,
            "outlier_gaps_excluded": 0,
            "raw_gaps": [],
            "typical_gaps": [],
        }

    raw_gaps = cycle_gaps_from_starts(ordered)
    typical = filter_typical_lengths(raw_gaps)
    outliers = len(raw_gaps) - len(typical)

    if not typical:
        return fallback, {
            "typical_cycles_used": 0,
            "outlier_gaps_excluded": outliers,
            "raw_gaps": raw_gaps,
            "typical_gaps": [],
        }

    recent = typical[-RECENT_TYPICAL_WINDOW:]
    estimated = int(round(median(recent)))
    return clamp_cycle_length(estimated, fallback), {
        "typical_cycles_used": len(recent),
        "outlier_gaps_excluded": outliers,
        "raw_gaps": raw_gaps,
        "typical_gaps": typical,
    }


def find_unusual_gap_with_previous(starts, new_start):
    """
    If inserting/comparing new_start against existing starts creates an unusual
    gap with the immediately previous start, return that context.
    """
    if not new_start:
        return None

    prior = [s for s in starts if s < new_start]
    if not prior:
        return None

    previous = max(prior)
    gap_days = (new_start - previous).days
    if not is_unusual_gap(gap_days):
        return None

    return {
        "previous_start": previous,
        "new_start": new_start,
        "gap_days": gap_days,
    }


def compute_phase_schedule(cycle_length: int, period_length: int) -> dict:
    """
    Map cycle days to phases using a standard gynecological model:
    - Menstruation: days 1..period_length
    - Follicular: after period until ovulation window
    - Ovulation: 3-day fertile window centred ~14 days before next period
    - Luteal: after ovulation until cycle end (PMS = last 7 days)
    """
    cycle_length = clamp_cycle_length(cycle_length)
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
            "typical_cycles_used": 0,
            "outlier_gaps_excluded": 0,
        }

    starts = sorted(c.cycle_start_date for c in cycles if c.cycle_start_date)
    estimated, meta = estimate_cycle_length(starts, default_cycle)
    raw_gaps = meta["raw_gaps"]
    typical_gaps = meta["typical_gaps"]

    period_lengths = [
        (c.cycle_end_date - c.cycle_start_date).days + 1
        for c in cycles
        if c.cycle_end_date and c.cycle_start_date
    ]

    return {
        "average_cycle_length": estimated,
        "average_period_length": (
            round(sum(period_lengths) / len(period_lengths)) if period_lengths else default_period
        ),
        # Keep raw extremes for awareness; prediction uses typical gaps only.
        "longest_cycle": max(raw_gaps) if raw_gaps else None,
        "shortest_cycle": min(raw_gaps) if raw_gaps else None,
        "longest_typical_cycle": max(typical_gaps) if typical_gaps else None,
        "shortest_typical_cycle": min(typical_gaps) if typical_gaps else None,
        "logged_cycles": len(cycles),
        "typical_cycles_used": meta["typical_cycles_used"],
        "outlier_gaps_excluded": meta["outlier_gaps_excluded"],
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


def _prediction_quality(stats, default_cycle):
    typical_used = stats.get("typical_cycles_used") or 0
    outliers = stats.get("outlier_gaps_excluded") or 0
    if typical_used >= 3:
        quality = "good"
    elif typical_used >= 1:
        quality = "fair"
    else:
        quality = "fallback"

    return {
        "quality": quality,
        "typical_cycles_used": typical_used,
        "outlier_gaps_excluded": outliers,
        "using_profile_default": typical_used == 0,
        "assumed_cycle_length": stats.get("average_cycle_length") or default_cycle,
    }


def compute_cycle_insights(user, reference_date=None):
    reference_date = reference_date or date.today()
    health = user.health_profile
    cycles = list(user.cycle_history_logs or [])

    latest = max(cycles, key=lambda c: c.cycle_start_date) if cycles else None
    last_start = latest.cycle_start_date if latest else None
    if not last_start and health and health.last_period_start:
        last_start = health.last_period_start

    default_cycle = health.average_cycle_length if health and health.average_cycle_length else 28
    default_cycle = clamp_cycle_length(default_cycle)
    default_period = health.average_period_length if health and health.average_period_length else 5
    stats = _cycle_statistics(cycles, default_cycle, default_period)

    avg_cycle = clamp_cycle_length(stats["average_cycle_length"] or default_cycle, default_cycle)
    avg_period = stats["average_period_length"] or default_period
    prediction_quality = _prediction_quality(stats, default_cycle)

    if not last_start:
        payload = _empty_insights()
        payload["statistics"] = stats
        payload["prediction_quality"] = prediction_quality
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
        "prediction_quality": prediction_quality,
        "statistics": stats,
    }
