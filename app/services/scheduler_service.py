import os

_scheduler = None


def init_scheduler(app):
    """Start APScheduler when ENABLE_SCHEDULER is set (avoids double-run in debug reloader)."""
    global _scheduler

    if not os.getenv("ENABLE_SCHEDULER", "").lower() in ("true", "1", "yes"):
        return

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and app.debug:
        return

    if _scheduler is not None:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        app.logger.warning("APScheduler not installed; scheduled jobs disabled.")
        return

    from app.services.push_notification_service import run_scheduled_notifications

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        func=lambda: _run_with_app_context(app, run_scheduled_notifications),
        trigger="interval",
        minutes=int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "1")),
        id="push_notifications",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    app.logger.info("APScheduler started for push notifications.")


def _run_with_app_context(app, func):
    with app.app_context():
        try:
            func()
        except Exception:
            app.logger.exception("Scheduled job failed.")
