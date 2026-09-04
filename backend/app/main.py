"""
FastAPI application entry point.

Lifespan:
  - Creates all DB tables on startup.
  - Starts APScheduler on startup and shuts it down on exit.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.core.config import get_settings
from backend.app.core.db import Base, engine
from backend.app.jobs.scheduler import get_scheduler
from backend.app.routers import (
    alerts,
    analysis,
    corporate_actions,
    prices,
    risk_profile,
    trades,
    watchlist,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("Starting APScheduler...")
    scheduler = get_scheduler()
    scheduler.start()

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
    allow_origins=settings.cors_origins,
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


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
