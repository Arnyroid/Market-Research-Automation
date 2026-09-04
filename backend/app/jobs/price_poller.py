"""
Price poller job.
Fetches LTP for every symbol in the watchlist and writes to price_history.
Runs every N minutes; skips silently outside market hours.
"""
from __future__ import annotations

from datetime import datetime

from loguru import logger

from backend.app.core.config import get_settings
from backend.app.core.db import SessionLocal
from backend.app.models import PriceHistory, Watchlist
from backend.app.services.data_fetch import fetch_quote

settings = get_settings()


def _is_market_hours() -> bool:
    now = datetime.now().strftime("%H:%M")
    return settings.market_open <= now <= settings.market_close


def run() -> None:
    if not _is_market_hours():
        return

    logger.info("price_poller: starting")
    db = SessionLocal()
    try:
        symbols = db.query(Watchlist).all()
        if not symbols:
            logger.info("price_poller: watchlist is empty, nothing to do")
            return

        added = 0
        for item in symbols:
            quote = fetch_quote(item.symbol, item.exchange)
            if quote is None:
                logger.warning(f"price_poller: no quote for {item.symbol}/{item.exchange}")
                continue

            row = PriceHistory(
                symbol=item.symbol,
                exchange=item.exchange,
                timestamp=datetime.now(),
                open=quote.open,
                high=quote.high,
                low=quote.low,
                close=quote.ltp,
                volume=quote.volume,
            )
            db.add(row)
            added += 1

        db.commit()
        logger.info(f"price_poller: stored {added}/{len(symbols)} quotes")
    except Exception as exc:
        logger.error(f"price_poller failed: {exc}")
        db.rollback()
    finally:
        db.close()
