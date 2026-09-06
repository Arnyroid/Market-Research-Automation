"""
Price poller job.
Fetches LTP for every symbol in the watchlist, writes to price_history,
and evaluates active alert rules on each fresh tick.
Runs every N minutes; skips silently outside market hours.

One row per (symbol, exchange, trading date) is enforced: if a row for
today already exists it is updated in-place (high/low/close/volume).
This prevents the chart from going flat due to duplicate intraday rows.
"""
from __future__ import annotations

from datetime import datetime, date

import pytz
from loguru import logger

from backend.app.core.config import get_settings
from backend.app.core.db import SessionLocal
from backend.app.models import PriceHistory, Watchlist
from backend.app.services.alert_engine import check_alerts
from backend.app.services.data_fetch import fetch_quote

settings = get_settings()


_IST = pytz.timezone("Asia/Kolkata")


def _ist_now() -> datetime:
    return datetime.now(_IST)


def _is_market_hours() -> bool:
    now = _ist_now().strftime("%H:%M")
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

        ist_today = _ist_now().date()
        today_start = datetime.combine(ist_today, datetime.min.time())
        upserted = 0

        for item in symbols:
            quote = fetch_quote(item.symbol, item.exchange)
            if quote is None:
                logger.warning(f"price_poller: no quote for {item.symbol}/{item.exchange}")
                continue

            # Grab previous close (last row BEFORE today) for pct-change alerts
            prev_row = (
                db.query(PriceHistory)
                .filter(
                    PriceHistory.symbol == item.symbol,
                    PriceHistory.exchange == item.exchange,
                    PriceHistory.timestamp < today_start,
                )
                .order_by(PriceHistory.timestamp.desc())
                .first()
            )
            prev_price = prev_row.close if prev_row else None

            # Upsert: update today's row if it already exists, else insert
            today_row = (
                db.query(PriceHistory)
                .filter(
                    PriceHistory.symbol == item.symbol,
                    PriceHistory.exchange == item.exchange,
                    PriceHistory.timestamp >= today_start,
                )
                .first()
            )

            if today_row is not None:
                # Update in-place: refresh close, track intraday high/low
                today_row.close = quote.ltp
                if quote.high is not None:
                    today_row.high = max(today_row.high or 0, quote.high)
                if quote.low is not None and quote.low > 0:
                    today_row.low = min(today_row.low or float("inf"), quote.low)
                if quote.volume is not None:
                    today_row.volume = quote.volume
            else:
                row = PriceHistory(
                    symbol=item.symbol,
                    exchange=item.exchange,
                    timestamp=today_start,   # noon-midnight of today for clean date key
                    open=quote.open,
                    high=quote.high,
                    low=quote.low,
                    close=quote.ltp,
                    volume=quote.volume,
                )
                db.add(row)

            upserted += 1

            # Evaluate alert rules for this symbol
            check_alerts(item.symbol, item.exchange, quote.ltp, prev_price, db)

        db.commit()
        logger.info(f"price_poller: upserted {upserted}/{len(symbols)} quotes")
    except Exception as exc:
        logger.error(f"price_poller failed: {exc}")
        db.rollback()
    finally:
        db.close()
