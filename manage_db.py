"""Database management CLI for Penmozhi API.

Examples:
    python manage_db.py status
    python manage_db.py migrate -m "add column"
    python manage_db.py upgrade
    python manage_db.py downgrade
    python manage_db.py clear
    python manage_db.py truncate
    python manage_db.py reset
    python manage_db.py seed
"""

import argparse
import os
import sys

from sqlalchemy import text


def _is_development():
    return os.getenv("FLASK_ENV", "").lower() == "development" or os.getenv(
        "FLASK_DEBUG", ""
    ).lower() in ("true", "1", "yes")


def cmd_status(app):
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from app.controllers.admin_controller import APPLICATION_MODELS
    from app.extensions import db

    with app.app_context():
        db.session.execute(text("SELECT 1"))

        table_counts = {}
        for model in APPLICATION_MODELS:
            table_counts[model.__tablename__] = db.session.query(model).count()

        migrate_ext = app.extensions["migrate"]
        config = migrate_ext.migrate.get_config()
        script = ScriptDirectory.from_config(config)

        with db.engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()

        head_revision = script.get_current_head()

        print("Database status:")
        print(f"  health: healthy")
        print(f"  total_records: {sum(table_counts.values())}")
        print(f"  table_counts: {table_counts}")
        print(f"  current_revision: {current_revision}")
        print(f"  head_revision: {head_revision}")
        print(f"  pending_upgrade: {current_revision != head_revision}")
    return 0


def cmd_migrate(app, message):
    from flask_migrate import migrate

    with app.app_context():
        migrate(message=message)
    print(f"Migration created: {message}")
    return 0


def cmd_upgrade(app):
    from flask_migrate import upgrade

    with app.app_context():
        upgrade()
    print("Migrations applied.")
    return 0


def cmd_downgrade(app):
    if not _is_development():
        print("Downgrade is allowed only in development. Set FLASK_ENV=development.")
        return 1

    from flask_migrate import downgrade

    with app.app_context():
        downgrade()
    print("Last migration rolled back.")
    return 0


def cmd_clear(app):
    from app.controllers.admin_controller import DELETE_ORDER
    from app.extensions import db

    with app.app_context():
        for model in DELETE_ORDER:
            db.session.query(model).delete(synchronize_session=False)
        db.session.commit()
        print("All rows deleted. AUTO_INCREMENT values were not reset.")
    return 0


def cmd_truncate(app):
    from app.controllers.admin_controller import DELETE_ORDER
    from app.extensions import db

    with app.app_context():
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for model in DELETE_ORDER:
            db.session.execute(text(f"TRUNCATE TABLE `{model.__tablename__}`"))
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()
        print("All tables truncated. New records will start from id=1.")
    return 0


def cmd_reset(app):
    if not _is_development():
        print("Reset is allowed only in development. Set FLASK_ENV=development.")
        return 1

    from app.extensions import db

    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()
        print("Database dropped and recreated.")
    return 0


def cmd_seed(app):
    from app.extensions import db
    from app.seeders.user_seeder import seed_education, seed_health_data, seed_users

    with app.app_context():
        db.create_all()
        seed_users()
        seed_education()
        seed_health_data()
        print("Seed data created.")
    return 0


def cmd_apply_manual(app):
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parent / "scripts" / "apply_manual_migrations.py"
    result = subprocess.run([sys.executable, str(script)], check=False)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Penmozhi database management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show database and migration status")
    sub.add_parser("upgrade", help="Apply pending migrations")
    sub.add_parser("downgrade", help="Roll back one migration (development only)")
    sub.add_parser("clear", help="Delete all rows (AUTO_INCREMENT not reset)")
    sub.add_parser(
        "truncate",
        help="Truncate all tables and reset AUTO_INCREMENT to 1",
    )
    sub.add_parser("reset", help="Drop and recreate all tables (development only)")
    sub.add_parser("seed", help="Run all seeders")

    sub.add_parser("apply-manual", help="Apply manual SQL migrations (onboarding + daily logs)")

    migrate_parser = sub.add_parser("migrate", help="Create a new migration")
    migrate_parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Migration description",
    )

    args = parser.parse_args()

    from app import create_app

    app = create_app()

    commands = {
        "status": lambda: cmd_status(app),
        "migrate": lambda: cmd_migrate(app, args.message),
        "upgrade": lambda: cmd_upgrade(app),
        "downgrade": lambda: cmd_downgrade(app),
        "clear": lambda: cmd_clear(app),
        "truncate": lambda: cmd_truncate(app),
        "reset": lambda: cmd_reset(app),
        "seed": lambda: cmd_seed(app),
        "apply-manual": lambda: cmd_apply_manual(app),
    }

    return commands[args.command]()


if __name__ == "__main__":
    sys.exit(main())
