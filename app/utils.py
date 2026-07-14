from datetime import date, datetime, time, timezone

PUBLIC_REGISTER_ROLES = ("user",)
ALL_ROLES = ("user", "admin")
LANGUAGE_PREFERENCES = ("tamil", "english")


def utc_now():
    return datetime.now(timezone.utc)


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def parse_time(value):
    if value is None:
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    if not text:
        return None
    parts = text.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(float(parts[2])) if len(parts) > 2 else 0
    return time(hour=hour, minute=minute, second=second)


def calculate_bmi(weight, height):
    """Compute BMI from weight (kg) and height (cm if > 3, else meters)."""
    if weight is None or height is None:
        return None
    try:
        w = float(weight)
        h = float(height)
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    height_m = h / 100.0 if h > 3 else h
    if height_m <= 0:
        return None
    return round(w / (height_m * height_m), 2)
