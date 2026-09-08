"""
Price poller job.
Fetches LTP for every symbol in the watchlist, writes to price_history,
and evaluates active alert rules on each fresh tick.
Runs every N minutes; skips silently outside market hours.

One row per (symbol, exchange, trading date) is enforced: if a row for
today already exists it is updated in-place (high/low/close/volume).
This prevents the chart from going flat due to duplicate intraday rows.

Fetch strategy: all yfinance calls are fanned out in parallel using
ThreadPoolExecutor, then DB writes and alert checks happen serially
(SQLite is single-writer).  Results are written to the in-process quote
cache so that API endpoints can serve subsequent requests from memory.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date

import pytz
from loguru import logger

from backend.app.core.config import get_settings
from backend.app.core.db import SessionLocal

from backend.app.models import Alert, PriceHistory, Watchlist
from backend.app.services.alert_engine import check_alerts
from backend.app.services.data_fetch import fetch_quote, QuoteResult

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

        # ── Phase 1: fetch all watchlist quotes in parallel ───────────────────
        # fetch_quote() writes each result into the in-process cache automatically.
        quotes: dict[int, QuoteResult] = {}   # watchlist item id → quote

        def _fetch_one(item: Watchlist) -> tuple[int, QuoteResult | None]:
            return item.id, fetch_quote(item.symbol, item.exchange)

        if symbols:
            with ThreadPoolExecutor(max_workers=min(20, len(symbols))) as pool:
                futures = {pool.submit(_fetch_one, item): item for item in symbols}
                for future in as_completed(futures):
                    item_id, quote = future.result()
                    if quote is not None:
                        quotes[item_id] = quote
                    else:
                        item = futures[future]
                        logger.warning(f"price_poller: no quote for {item.symbol}/{item.exchange}")

            logger.info(f"price_poller: fetched {len(quotes)}/{len(symbols)} quotes")

        # ── Phase 2: DB writes + alert checks (serial — SQLite is single-writer)
        ist_today = _ist_now().date()
        today_start = datetime.combine(ist_today, datetime.min.time())
        upserted = 0

        # Build set of (symbol, exchange) already covered by the watchlist
        watchlist_keys: set[tuple[str, str]] = {
            (item.symbol, item.exchange) for item in symbols
        }

        for item in symbols:
            quote = quotes.get(item.id)
            if quote is None:
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
        if symbols:
            logger.info(f"price_poller: upserted {upserted}/{len(symbols)} quotes")

        # ── Phase 3: alerts for non-watchlist symbols ─────────────────────────
        # Find distinct (symbol, exchange) pairs that have active alerts but are
        # NOT on the watchlist.  We only need their current price — no DB write.
        off_watch_rows = (
            db.query(Alert.symbol, Alert.exchange)
            .filter(Alert.active == True)  # noqa: E712
            .distinct()
            .all()
        )
        off_watch = [
            (row.symbol, row.exchange)
            for row in off_watch_rows
            if (row.symbol, row.exchange) not in watchlist_keys
        ]

        if off_watch:
            logger.info(
                f"price_poller: checking alerts for {len(off_watch)} non-watchlist symbol(s): "
                + ", ".join(f"{s}/{e}" for s, e in off_watch)
            )

            # Fetch quotes in parallel (best-effort — no PriceHistory writes)
            def _fetch_sym(sym_exc: tuple[str, str]) -> tuple[tuple[str, str], QuoteResult | None]:
                s, e = sym_exc
                return (s, e), fetch_quote(s, e)

            off_quotes: dict[tuple[str, str], QuoteResult] = {}
            with ThreadPoolExecutor(max_workers=min(20, len(off_watch))) as pool:
                futures2 = {pool.submit(_fetch_sym, se): se for se in off_watch}
                for future in as_completed(futures2):
                    key, quote = future.result()
                    if quote is not None:
                        off_quotes[key] = quote
                    else:
                        logger.warning(
                            f"price_poller: no quote for non-watchlist {key[0]}/{key[1]}"
                        )

            # Evaluate alerts (no PriceHistory upsert for non-watchlist symbols)
            for (sym, exc), quote in off_quotes.items():
                check_alerts(sym, exc, quote.ltp, None, db)

            db.commit()
            logger.info(
                f"price_poller: evaluated non-watchlist alerts for "
                f"{len(off_quotes)}/{len(off_watch)} symbols"
            )

    except Exception as exc:
        logger.error(f"price_poller failed: {exc}")
        db.rollback()
    finally:
        db.close()
