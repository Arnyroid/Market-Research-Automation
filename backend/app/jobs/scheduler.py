"""
APScheduler setup — registers all background jobs and exposes a singleton
scheduler that main.py starts/stops in the FastAPI lifespan.

Jobs registered
---------------
  price_poller          every N minutes during market hours
  indicator_calculator  end-of-day (16:00 IST)
  feedback_evaluator    daily at 17:00 IST (post-market)

NOTE: agent_runner is intentionally NOT scheduled.
  AI analysis (Gemini) is triggered on-demand only — when the user opens a
  stock detail page or clicks "Refresh Insight". This avoids burning the free
  Gemini quota with N silent API calls every morning for every watchlist symbol.
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from backend.app.core.config import get_settings
from backend.app.jobs import (
    feedback_evaluator,
    indicator_calculator,
    price_poller,
)

settings = get_settings()

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Return the singleton scheduler, creating it if needed."""
    global _scheduler
    if _scheduler is None:
        _scheduler = _build_scheduler()
    return _scheduler


def _build_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="Asia/Kolkata")

    # ── Price poller (every N min, market hours only — the job checks internally) ──
    sched.add_job(
        price_poller.run,
        trigger=IntervalTrigger(minutes=settings.price_poll_interval_minutes),
        id="price_poller",
        name="Price Poller",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # ── Indicator calculator — end-of-day at 16:00 IST ───────────────────────
    sched.add_job(
        indicator_calculator.run,
        trigger=CronTrigger(hour=16, minute=0, timezone="Asia/Kolkata"),
        id="indicator_calculator",
        name="Indicator Calculator",
        replace_existing=True,
    )

    # ── Feedback evaluator — daily at 17:00 IST ───────────────────────────────
    sched.add_job(
        feedback_evaluator.run,
        trigger=CronTrigger(hour=17, minute=0, timezone="Asia/Kolkata"),
        id="feedback_evaluator",
        name="Feedback Evaluator",
        replace_existing=True,
    )

    logger.info("APScheduler configured with all jobs")
    return sched
