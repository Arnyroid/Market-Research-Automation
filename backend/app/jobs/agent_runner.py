"""
Agent runner job.
Runs ai_agent.run_analysis() for every watchlist symbol and persists results.
Runs daily at 08:00 IST; can also be triggered on-demand via the API.
"""
from __future__ import annotations

from loguru import logger

from backend.app.core.db import SessionLocal
from backend.app.models import Watchlist
from backend.app.services.ai_agent import run_analysis


def run() -> None:
    logger.info("agent_runner: starting")
    db = SessionLocal()
    try:
        symbols = db.query(Watchlist).all()
        if not symbols:
            logger.info("agent_runner: watchlist is empty")
            return

        for item in symbols:
            try:
                analysis = run_analysis(item.symbol, item.exchange, db)
                if analysis is not None:
                    db.add(analysis)
                    db.commit()
                    logger.info(
                        f"agent_runner: stored analysis for {item.symbol} "
                        f"(risk_flag={analysis.risk_flag})"
                    )
            except Exception as exc:
                logger.error(f"agent_runner: failed for {item.symbol}: {exc}")
                db.rollback()
    except Exception as exc:
        logger.error(f"agent_runner job failed: {exc}")
    finally:
        db.close()
