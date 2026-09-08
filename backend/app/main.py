"""
FastAPI application entry point.

Lifespan:
  - Creates all DB tables on startup.
  - Starts APScheduler on startup and shuts it down on exit.
  - Warms the in-process quote cache by fetching all watchlist symbols in background.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from loguru import logger

from backend.app.core.config import get_settings
from backend.app.core.db import Base, engine, SessionLocal
from backend.app.jobs.scheduler import get_scheduler
from backend.app.services.data_fetch import _ensure_nse_symbols, _ensure_bse_symbols
from backend.app.routers import (
    alerts,
    analysis,
    corporate_actions,
    market,
    prices,
    risk_profile,
    trades,
    watchlist,
)

settings = get_settings()


def _warm_quote_cache() -> None:
    """
    Background task: fetch live quotes for every watchlist symbol at startup
    so the first page load is served from cache rather than hitting yfinance cold.
    Runs in a daemon thread — any exception is logged and silently swallowed.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from backend.app.models import Watchlist
    from backend.app.services.data_fetch import fetch_quote

    def _do_warm():
        try:
            db = SessionLocal()
            try:
                symbols = db.query(Watchlist).all()
            finally:
                db.close()
            if not symbols:
                return
            logger.info(f"cache warm-up: fetching {len(symbols)} watchlist symbols…")
            with ThreadPoolExecutor(max_workers=min(20, len(symbols))) as pool:
                futures = {pool.submit(fetch_quote, item.symbol, item.exchange): item for item in symbols}
                ok = sum(1 for f in as_completed(futures) if f.result() is not None)
            logger.info(f"cache warm-up: {ok}/{len(symbols)} symbols cached")
        except Exception as exc:
            logger.warning(f"cache warm-up failed (non-fatal): {exc}")

    threading.Thread(target=_do_warm, daemon=True, name="quote-cache-warmup").start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("Pre-loading NSE + BSE equity masters…")
    import threading
    threading.Thread(target=_ensure_nse_symbols, daemon=True).start()
    threading.Thread(target=_ensure_bse_symbols, daemon=True).start()

    logger.info("Starting APScheduler...")
    scheduler = get_scheduler()
    scheduler.start()

    # Warm the quote cache in background — first page load will be instant
    _warm_quote_cache()

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down APScheduler...")
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Stock Watchlist & AI Trading Assistant",
    description="Personal Indian equities tracker with AI-driven insights.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(watchlist.router,         prefix="/watchlist",        tags=["Watchlist"])
app.include_router(alerts.router,            prefix="/alerts",           tags=["Alerts"])
app.include_router(prices.router,            prefix="/prices",           tags=["Prices"])
app.include_router(analysis.router,          prefix="/analysis",         tags=["Analysis"])
app.include_router(risk_profile.router,      prefix="/risk-profile",     tags=["Risk Profile"])
app.include_router(trades.router,            prefix="/trades",           tags=["Trades"])
app.include_router(corporate_actions.router, prefix="/corporate-actions",tags=["Corporate Actions"])
app.include_router(market.router,            prefix="/market",           tags=["Market"])


@app.get("/", include_in_schema=False)
def root():
    """Redirect browser visits to the interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/health/scheduler", tags=["Health"])
def health_scheduler():
    """
    Returns scheduler status, all registered jobs, their next fire times,
    and whether the scheduler is currently running.
    """
    from datetime import timezone
    sched = get_scheduler()
    jobs = []
    for job in sched.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id":          job.id,
            "name":        job.name,
            "next_run_utc": next_run.astimezone(timezone.utc).isoformat() if next_run else None,
            "next_run_ist": next_run.isoformat() if next_run else None,
            "trigger":     str(job.trigger),
        })
    return {
        "running": sched.running,
        "jobs":    jobs,
    }
