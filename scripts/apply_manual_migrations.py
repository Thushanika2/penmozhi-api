"""Apply manual SQL migrations safely (skips existing columns/tables)."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.extensions import db


def column_exists(table: str, column: str) -> bool:
    inspector = inspect(db.engine)
    return column in {col["name"] for col in inspector.get_columns(table)}


def table_exists(table: str) -> bool:
    return table in inspect(db.engine).get_table_names()


def add_column(table: str, definition: str) -> None:
    name = definition.strip().split()[0]
    if column_exists(table, name):
        print(f"  skip column {table}.{name}")
        return
    db.session.execute(text(f"ALTER TABLE `{table}` ADD COLUMN {definition}"))
    db.session.commit()
    print(f"  added column {table}.{name}")


def run_sql(sql: str) -> None:
    for statement in [part.strip() for part in sql.split(";") if part.strip()]:
        if statement.upper().startswith("UPDATE "):
            db.session.execute(text(statement))
            db.session.commit()
            print("  ran update")
            continue
        db.session.execute(text(statement))
        db.session.commit()
        print(f"  ran: {statement[:60]}...")


def main() -> int:
    app = create_app()
    with app.app_context():
        print("Applying onboarding module columns...")
        add_column("user_profiles", "country VARCHAR(100) NULL")
        add_column("user_profiles", "timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata'")
        add_column("user_profiles", "onboarding_completed TINYINT(1) NOT NULL DEFAULT 0")

        health_columns = [
            "menarche_age INT NULL",
            "average_cycle_length INT NULL DEFAULT 28",
            "average_period_length INT NULL DEFAULT 5",
            "last_period_start DATE NULL",
            "typical_flow VARCHAR(20) NULL",
            "cycle_regularity VARCHAR(20) NULL",
            "common_symptoms JSON NULL",
            "health_conditions JSON NULL",
            "sleep_hours FLOAT NULL",
            "water_intake_liters FLOAT NULL",
            "exercise_frequency VARCHAR(30) NULL",
            "stress_level VARCHAR(20) NULL",
            "smoking TINYINT(1) NOT NULL DEFAULT 0",
            "alcohol TINYINT(1) NOT NULL DEFAULT 0",
            "trying_to_conceive TINYINT(1) NOT NULL DEFAULT 0",
            "is_pregnant TINYINT(1) NOT NULL DEFAULT 0",
            "is_breastfeeding TINYINT(1) NOT NULL DEFAULT 0",
            "using_birth_control TINYINT(1) NOT NULL DEFAULT 0",
            "birth_control_type VARCHAR(50) NULL",
            "notify_period TINYINT(1) NOT NULL DEFAULT 1",
            "notify_ovulation TINYINT(1) NOT NULL DEFAULT 1",
            "notify_medication TINYINT(1) NOT NULL DEFAULT 1",
            "notify_daily_health TINYINT(1) NOT NULL DEFAULT 1",
            "updated_at DATETIME NULL",
        ]
        for col in health_columns:
            add_column("health_profiles", col)

        if not table_exists("password_reset_tokens"):
            run_sql(
                """
                CREATE TABLE password_reset_tokens (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  user_id INT NOT NULL,
                  token_hash VARCHAR(255) NOT NULL UNIQUE,
                  expires_at DATETIME NOT NULL,
                  used_at DATETIME NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES user_profiles(id)
                )
                """
            )
        else:
            print("  skip table password_reset_tokens")

        print("Applying daily logs module...")
        add_column("cycle_history_logs", "notes TEXT NULL")

        if not table_exists("daily_logs"):
            run_sql(
                """
                CREATE TABLE daily_logs (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  profile_id INT NOT NULL,
                  log_date DATE NOT NULL,
                  flow_level VARCHAR(20) NULL,
                  pain_level VARCHAR(20) NULL,
                  mood VARCHAR(50) NULL,
                  energy VARCHAR(20) NULL,
                  sleep_hours FLOAT NULL,
                  exercise VARCHAR(50) NULL,
                  weight FLOAT NULL,
                  basal_temp FLOAT NULL,
                  cervical_fluid VARCHAR(20) NULL,
                  sexual_activity TINYINT(1) NOT NULL DEFAULT 0,
                  notes TEXT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  FOREIGN KEY (profile_id) REFERENCES user_profiles(id),
                  UNIQUE KEY uq_daily_log_profile_date (profile_id, log_date)
                )
                """
            )
        else:
            print("  skip table daily_logs")

        db.session.execute(
            text(
                """
                UPDATE user_profiles SET onboarding_completed = 1
                WHERE onboarding_completed = 0 AND id IN (
                  SELECT profile_id FROM health_profiles WHERE last_period_start IS NOT NULL
                )
                """
            )
        )
        db.session.commit()
        print("Migrations complete.")

        print("Making user_profiles.date_of_birth nullable...")
        try:
            db.session.execute(
                text("ALTER TABLE `user_profiles` MODIFY COLUMN date_of_birth DATE NULL")
            )
            db.session.commit()
            print("  updated user_profiles.date_of_birth to nullable")
        except Exception as exc:
            db.session.rollback()
            print(f"  skip date_of_birth nullable migration: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
