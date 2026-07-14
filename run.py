import logging
import os
import time

from flask_cors import CORS

from app import create_app

app = create_app()
CORS(app)

logger = logging.getLogger(__name__)


def initialize_database(max_retries=10, retry_delay=3):
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        logger.warning("Database URI is not configured; skipping table creation.")
        return

    from app.extensions import db

    for attempt in range(1, max_retries + 1):
        try:
            with app.app_context():
                db.create_all()
            return
        except Exception as exc:
            if attempt == max_retries:
                logger.exception("Database initialization failed after %s attempts.", max_retries)
                raise
            logger.warning(
                "Database initialization attempt %s/%s failed: %s",
                attempt,
                max_retries,
                exc,
            )
            time.sleep(retry_delay)


if os.getenv("RAILWAY_ENVIRONMENT"):
    try:
        initialize_database()
    except Exception:
        logger.exception("Continuing startup without initialized database tables.")

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
