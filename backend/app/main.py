"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
import os
from datetime import datetime

from .db import init_db
from .routers import watchlist, alerts, prices, analysis, risk_profile
from .jobs import SchedulerJobs

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Stock Watchlist & AI Trading Assistant",
    description="Personal stock watchlist with AI-powered trend analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(watchlist.router)
app.include_router(alerts.router)
app.include_router(prices.router)
app.include_router(analysis.router)
app.include_router(risk_profile.router)

# Initialize scheduler
scheduler = BackgroundScheduler()


@app.on_event("startup")
async def startup_event():
    """Start background scheduler on app startup"""
    logger.info("Starting up application...")
    
    # Schedule jobs
    try:
        # Price poller: every 5 minutes during market hours (9:15 to 15:30 IST)
        scheduler.add_job(
            SchedulerJobs.price_poller,
            trigger=IntervalTrigger(minutes=5),
            id="price_poller",
            name="Price Poller",
            replace_existing=True
        )
        
        # Alert checker: every 5 minutes during market hours
        scheduler.add_job(
            SchedulerJobs.alert_checker,
            trigger=IntervalTrigger(minutes=5),
            id="alert_checker",
            name="Alert Checker",
            replace_existing=True
        )
        
        # Indicator calculator: daily at 16:00 IST (after market close)
        scheduler.add_job(
            SchedulerJobs.indicator_calculator,
            trigger=CronTrigger(hour=16, minute=0),  # UTC time, adjust as needed
            id="indicator_calculator",
            name="Indicator Calculator",
            replace_existing=True
        )
        
        # Agent runner: daily at 08:00 IST (before market open)
        scheduler.add_job(
            SchedulerJobs.agent_runner,
            trigger=CronTrigger(hour=2, minute=30),  # UTC time for 08:00 IST
            id="agent_runner",
            name="Agent Runner",
            replace_existing=True
        )
        
        # Feedback evaluator: daily at 17:00 IST
        scheduler.add_job(
            SchedulerJobs.feedback_evaluator,
            trigger=CronTrigger(hour=11, minute=30),  # UTC time for 17:00 IST
            id="feedback_evaluator",
            name="Feedback Evaluator",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully with all jobs registered")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler on app shutdown"""
    logger.info("Shutting down application...")
    scheduler.shutdown()
    logger.info("Scheduler shut down successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "scheduler_running": scheduler.running
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Stock Watchlist & AI Trading Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Load environment
    import dotenv
    dotenv.load_dotenv()
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "False") == "True"
    )
