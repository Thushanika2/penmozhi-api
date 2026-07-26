from datetime import timedelta

from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.utils import utc_now


PCOS_SYMPTOM_KEYS = {"acne", "weight_change", "weight gain", "weight loss", "hirsutism", "hair loss"}


def _long_cycles(cycles, min_length=35, consecutive=3):
    """Return windows where consecutive cycles exceed min_length days."""
    if len(cycles) < consecutive:
        return []

    sorted_cycles = sorted(cycles, key=lambda c: c.cycle_start_date)
    lengths = []
    for i in range(1, len(sorted_cycles)):
        delta = (sorted_cycles[i].cycle_start_date - sorted_cycles[i - 1].cycle_start_date).days
        lengths.append((delta, sorted_cycles[i - 1], sorted_cycles[i]))

    flagged = []
    streak = 0
    window_start = None
    window_cycles = []

    for length, prev_cycle, curr_cycle in lengths:
        if length >= min_length:
            streak += 1
            if streak == 1:
                window_start = prev_cycle
            window_cycles.append({"cycle": curr_cycle.to_dict(), "cycle_length_days": length})
        else:
            if streak >= consecutive:
                flagged.append({
                    "pattern": "long_cycles",
                    "description": (
                        f"{streak + 1} consecutive cycles over {min_length} days detected. "
                        "Discuss with a clinician — this is not a diagnosis."
                    ),
                    "triggered_logs": {
                        "cycles": [window_start.to_dict()] + window_cycles if window_start else window_cycles,
                    },
                })
            streak = 0
            window_start = None
            window_cycles = []

    if streak >= consecutive:
        flagged.append({
            "pattern": "long_cycles",
            "description": (
                f"{streak + 1} consecutive cycles over {min_length} days detected. "
                "Discuss with a clinician — this is not a diagnosis."
            ),
            "triggered_logs": {
                "cycles": [window_start.to_dict()] + window_cycles if window_start else window_cycles,
            },
        })

    return flagged


def _symptoms_in_window(symptoms, start_date, end_date):
    matched = []
    for symptom in symptoms:
        if not symptom.date_time:
            continue
        day = symptom.date_time.date()
        if start_date <= day <= end_date:
            cat = (symptom.category or "").lower()
            if any(key in cat for key in PCOS_SYMPTOM_KEYS):
                matched.append(symptom.to_dict())
    return matched


def detect_pcos_patterns(user):
    """
    Heuristic PCOS-related pattern flags from recent cycles and symptoms.
    Not a diagnosis — always frame for clinician discussion.
    """
    patterns = []
    cycles = (
        CycleHistoryLog.query.filter_by(profile_id=user.id)
        .order_by(CycleHistoryLog.cycle_start_date.desc())
        .limit(12)
        .all()
    )
    cycles = list(reversed(cycles))

    symptoms = (
        SymptomTrackingLog.query.filter_by(profile_id=user.id)
        .order_by(SymptomTrackingLog.date_time.desc())
        .limit(100)
        .all()
    )

    long_cycle_patterns = _long_cycles(cycles)
    for pattern in long_cycle_patterns:
        cycle_logs = pattern["triggered_logs"].get("cycles", [])
        if len(cycle_logs) >= 2:
            start = cycle_logs[0].get("cycle_start_date")
            end = cycle_logs[-1].get("cycle_start_date")
            if start and end:
                from app.utils import parse_date
                try:
                    s = parse_date(start)
                    e = parse_date(end)
                    matched_symptoms = _symptoms_in_window(symptoms, s, e)
                    if matched_symptoms:
                        pattern["triggered_logs"]["symptoms"] = matched_symptoms
                        pattern["description"] = (
                            "Long cycles combined with acne or weight-change symptoms "
                            "in the same window. Discuss with a clinician — this is not a diagnosis."
                        )
                except ValueError:
                    pass
        patterns.append(pattern)

    irregular = [c for c in cycles if c.cycle_end_date and c.cycle_start_date]
    if len(irregular) >= 4:
        lengths = []
        sorted_c = sorted(irregular, key=lambda c: c.cycle_start_date)
        for i in range(1, len(sorted_c)):
            lengths.append((sorted_c[i].cycle_start_date - sorted_c[i - 1].cycle_start_date).days)
        if lengths and max(lengths) - min(lengths) >= 14:
            high_pain = [s.to_dict() for s in symptoms if s.pain_severity >= 7]
            patterns.append({
                "pattern": "irregular_cycles",
                "description": (
                    "Highly variable cycle lengths detected. Discuss with a clinician — "
                    "this is not a diagnosis."
                ),
                "triggered_logs": {
                    "cycles": [c.to_dict() for c in sorted_c[-4:]],
                    "symptoms": high_pain[:5],
                },
            })

    return {
        "patterns": patterns,
        "disclaimer": (
            "These patterns are based on your logged data and are not a medical diagnosis. "
            "Please discuss any concerns with a qualified clinician."
        ),
        "analyzed_at": utc_now().isoformat(),
    }
