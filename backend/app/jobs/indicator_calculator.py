"""
Indicator calculator job.
Re-computes indicators for every watchlist symbol and logs a snapshot.
The snapshot itself is consumed by agent_runner; this job just ensures
the price_history is current enough for meaningful numbers.
"""
from __future__ import annotations

from loguru import logger

from backend.app.core.db import SessionLocal
from backend.app.models import Watchlist
from backend.app.services.indicators import compute_indicators


def run() -> None:
    logger.info("indicator_calculator: starting")
    db = SessionLocal()
    try:
        symbols = db.query(Watchlist).all()
        for item in symbols:
            snap = compute_indicators(item.symbol, item.exchange, db)
            if snap.errors:
                logger.warning(
                    f"indicator_calculator: {item.symbol}/{item.exchange} — {snap.errors}"
                )
            else:
                logger.info(
                    f"indicator_calculator: {item.symbol} RSI={snap.rsi_14} "
                    f"SMA20={snap.sma_20} vol={snap.realized_volatility_30d}%"
                )
    except Exception as exc:
        logger.error(f"indicator_calculator failed: {exc}")
    finally:
        db.close()
