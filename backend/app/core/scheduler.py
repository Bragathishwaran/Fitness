"""Background scheduler for daily workout reminders."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.notification_service import run_daily_jobs

logger = logging.getLogger("fittrack.scheduler")

_scheduler: BackgroundScheduler | None = None


def _run_reminder_job() -> None:
    """Run reminder generation with its own database session."""
    db = SessionLocal()
    try:
        result = run_daily_jobs(db)
        logger.info("Daily notification job completed: %s", result)
    except Exception:  # pragma: no cover - defensive logging for background job
        logger.exception("Daily notification job failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Start the scheduler once. Returns None when disabled."""
    global _scheduler
    if not settings.ENABLE_SCHEDULER:
        logger.info("Scheduler disabled by configuration")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_reminder_job,
        trigger="cron",
        hour=settings.REMINDER_HOUR,
        minute=settings.REMINDER_MINUTE,
        id="daily_workout_reminders",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: daily reminders at %02d:%02d UTC",
        settings.REMINDER_HOUR,
        settings.REMINDER_MINUTE,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the scheduler if it is running."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
