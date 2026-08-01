import logging
import os
import time

from flask_cors import CORS

from app import create_app
from app.config import Config

app = create_app()

_cors_origins = Config.CORS_ORIGINS
if _cors_origins and _cors_origins != "*":
    _cors_origins = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

CORS(
    app,
    origins=_cors_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

logger = logging.getLogger(__name__)


def run_migrations(max_retries=3, retry_delay=3):
    from flask_migrate import upgrade

    for attempt in range(1, max_retries + 1):
        try:
            with app.app_context():
                upgrade()
            logger.info("Database migrations applied successfully.")
            return True
        except Exception as exc:
            if attempt == max_retries:
                logger.exception("Database migration failed after %s attempts.", max_retries)
                return False
            logger.warning(
                "Database migration attempt %s/%s failed: %s",
                attempt,
                max_retries,
                exc,
            )
            time.sleep(retry_delay)
    return False


def initialize_database(max_retries=10, retry_delay=3):
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        logger.warning("Database URI is not configured; skipping table creation.")
        return False

    from app.extensions import db

    for attempt in range(1, max_retries + 1):
        try:
            with app.app_context():
                db.create_all()
            logger.info("Database create_all completed.")
            return True
        except Exception as exc:
            if attempt == max_retries:
                logger.exception("Database initialization failed after %s attempts.", max_retries)
                return False
            logger.warning(
                "Database initialization attempt %s/%s failed: %s",
                attempt,
                max_retries,
                exc,
            )
            time.sleep(retry_delay)
    return False


def apply_manual_schema_sync():
    """Fallback when alembic cannot upgrade because objects already exist."""
    try:
        from scripts.apply_manual_migrations import main as apply_manual

        code = apply_manual()
        logger.info("Manual schema sync finished with code %s.", code)
        return code == 0
    except Exception:
        logger.exception("Manual schema sync failed.")
        return False


def ensure_database_ready():
    if run_migrations():
        return

    logger.warning("Alembic upgrade failed; running create_all + manual schema sync.")
    initialize_database()
    apply_manual_schema_sync()

    # Retry upgrade once more now that conflicting objects should be handled
    # by idempotent migrations / manual sync.
    if not run_migrations():
        logger.error(
            "Database schema may still be incomplete. "
            "Check Railway MySQL variables and migration logs."
        )


if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_NAME"):
    try:
        ensure_database_ready()
    except Exception:
        logger.exception("Continuing startup without fully initialized database schema.")

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
