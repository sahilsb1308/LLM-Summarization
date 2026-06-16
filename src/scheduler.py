"""Weekly auto-scheduler: regenerates report every Monday at 08:00 UTC."""

import os
import json
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_weekly_refresh(include_competitive: bool = True):
    """Fetch fresh data and regenerate the report. Called by the scheduler."""
    from src.youtube import collect_all_data, save_data, MOVEUP_CHANNELS, COMPETITOR_CHANNELS
    from src.analyzer import generate_report, save_report

    logger.info(f"[Scheduler] Starting weekly refresh at {datetime.now(timezone.utc).isoformat()}")

    channels = dict(MOVEUP_CHANNELS)
    if include_competitive:
        channels.update(COMPETITOR_CHANNELS)

    try:
        data = collect_all_data(channels=channels)
        save_data(data)
        report = generate_report(data, include_competitive=include_competitive)
        save_report(report)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        save_data(data, f"data/reports/archive/data_{ts}.json")
        save_report(report, f"data/reports/archive/report_{ts}.md")

        logger.info("[Scheduler] Weekly refresh completed successfully.")
        return True
    except Exception as e:
        logger.error(f"[Scheduler] Weekly refresh failed: {e}")
        return False


def start_scheduler(include_competitive: bool = True):
    """Start the background scheduler (Monday 08:00 UTC)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        func=lambda: run_weekly_refresh(include_competitive),
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_report",
        name="Weekly YouTube Report Refresh",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[Scheduler] Started. Next run: every Monday at 08:00 UTC.")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("[Scheduler] Stopped.")


def get_next_run_time() -> str | None:
    global _scheduler
    if not _scheduler or not _scheduler.running:
        return None
    job = _scheduler.get_job("weekly_report")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M UTC")
    return None
