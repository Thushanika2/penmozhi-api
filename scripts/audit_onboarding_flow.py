"""Quick audit: register without DOB + complete onboarding."""

from __future__ import annotations

import json
import random
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:5000"


def post(path: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def main() -> int:
    email = f"audit-{random.randint(100000, 999999)}@penmozhi.com"
    password = "User123!"

    reg = post(
        "/api/auth/register",
        {
            "full_name": "Audit User",
            "email": email,
            "password": password,
            "language_preference": "english",
        },
    )
    print("register OK:", reg["user"]["email"], "dob=", reg["user"].get("date_of_birth"))

    login = post("/api/auth/login", {"email": email, "password": password})
    token = login["access_token"]
    print("login OK")

    last = date.today() - timedelta(days=5)
    payload = {
        "full_name": "Audit User",
        "date_of_birth": "1998-05-15",
        "country": "India",
        "height": 165,
        "weight": 58,
        "language_preference": "english",
        "timezone": "Asia/Kolkata",
        "knows_last_three_months": True,
        "period_history": [
            {"period_start": last.isoformat(), "flow": "medium"},
            {"period_start": (last - timedelta(days=28)).isoformat(), "flow": "light"},
            {"period_start": (last - timedelta(days=56)).isoformat(), "flow": "medium"},
        ],
        "average_cycle_length": 28,
        "common_symptoms": ["cramps"],
        "health_conditions": ["none"],
        "sleep_hours": 7,
        "water_intake_liters": 2,
        "exercise_frequency": "weekly",
        "stress_level": "medium",
        "smoking": False,
        "alcohol": False,
        "trying_to_conceive": False,
        "is_teenager": False,
        "is_pregnant": False,
        "is_breastfeeding": False,
        "using_birth_control": False,
        "birth_control_type": "none",
        "notify_period": True,
        "notify_ovulation": True,
        "notify_medication": True,
        "notify_daily_health": True,
    }

    try:
        done = post("/api/onboarding/complete", payload, token=token)
    except urllib.error.HTTPError as exc:
        print("onboarding FAIL:", exc.read().decode())
        return 1

    print(
        "onboarding OK:",
        done.get("message"),
        "completed=",
        done["user"].get("onboarding_completed"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
