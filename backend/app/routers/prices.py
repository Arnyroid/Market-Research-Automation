"""
Prices router — latest quotes, OHLCV history, and a WebSocket push channel.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.db import SessionLocal, get_db
from backend.app.models import PriceHistory, Watchlist
from backend.app.services.data_fetch import (
    fetch_ohlcv, fetch_quote,
    get_cached_quote, get_all_cached_quotes,
)

router = APIRouter()
settings = get_settings()


# ── Schemas ───────────────────────────────────────────────────────────────────

class QuoteOut(BaseModel):
    symbol: str
    exchange: str
    company_name: str | None
    ltp: float
    open: float | None
    high: float | None
    low: float | None
    prev_close: float | None
    volume: int | None
    pct_change: float | None


class OHLCVOut(BaseModel):
    timestamp: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None

    model_config = {"from_attributes": True}


# ── REST endpoints ────────────────────────────────────────────────────────────

class BatchQuoteRequest(BaseModel):
    symbols: list[dict]   # [{"symbol": "RELIANCE", "exchange": "NSE"}, ...]


def _to_quote_out(q: "object") -> QuoteOut:  # type: ignore[override]
    return QuoteOut(
        symbol=q.symbol,          # type: ignore[attr-defined]
        exchange=q.exchange,
        company_name=q.company_name or None,
        ltp=q.ltp,
        open=q.open,
        high=q.high,
        low=q.low,
        prev_close=q.prev_close,
        volume=q.volume,
        pct_change=q.pct_change,
    )


@router.post("/batch", response_model=list[QuoteOut])
def get_quotes_batch(payload: BatchQuoteRequest):
    """
    Cache-first batch quote fetch.

    Flow:
      1. Check the in-process quote cache for each symbol.
      2. Symbols found in cache → returned immediately (0 ms).
      3. Cache-miss symbols → fetched in parallel via ThreadPoolExecutor,
         written to cache, then returned.

    On first load (cold cache) all symbols are fetched in parallel — ~1-2 s.
    On subsequent loads (warm cache, populated by the price poller every 5 min)
    the entire response is served from memory — <5 ms.
    """
    items = payload.symbols[:60]
    results: list[QuoteOut] = []
    misses: list[dict] = []

    # ── Cache hit pass ────────────────────────────────────────────────────────
    for item in items:
        sym  = item.get("symbol", "")
        exch = item.get("exchange", "NSE").upper()
        cached = get_cached_quote(sym, exch)
        if cached is not None:
            results.append(_to_quote_out(cached))
        else:
            misses.append(item)

    # ── Parallel yfinance fetch for cache misses only ─────────────────────────
    if misses:
        def _fetch(item: dict) -> QuoteOut | None:
            sym  = item.get("symbol", "")
            exch = item.get("exchange", "NSE").upper()
            try:
                q = fetch_quote(sym, exch)   # also writes to cache
                return _to_quote_out(q) if q else None
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=min(20, len(misses))) as pool:
            futures = {pool.submit(_fetch, item): item for item in misses}
            for future in as_completed(futures):
                r = future.result()
                if r is not None:
                    results.append(r)

    return results


@router.get("/{symbol}", response_model=QuoteOut)
def get_quote(symbol: str, exchange: str = "NSE"):
    """Cache-first single quote. Hits yfinance only on a cache miss."""
    cached = get_cached_quote(symbol, exchange.upper())
    if cached is not None:
        return _to_quote_out(cached)
    quote = fetch_quote(symbol, exchange.upper())
    if quote is None:
        raise HTTPException(status_code=503, detail="Could not fetch quote — exchange API unavailable")
    return _to_quote_out(quote)


@router.get("/{symbol}/history", response_model=list[OHLCVOut])
def get_history(
    symbol: str,
    exchange: str = "NSE",
    days: int = 30,
    db: Session = Depends(get_db),
):
    # Cap at 400 calendar days (~280 trading days — enough for SMA-200)
    days = min(days, 400)
    since = datetime.now() - timedelta(days=days)
    rows = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.symbol == symbol,
            PriceHistory.exchange == exchange.upper(),
            PriceHistory.timestamp >= since,
        )
        .order_by(PriceHistory.timestamp.asc())
        .all()
    )

    # Deduplicate by calendar date: keep the last row per date.
    seen_dates: set[str] = set()
    deduped: list[PriceHistory] = []
    for row in reversed(rows):                      # most-recent first
        day = row.timestamp.date().isoformat()
        if day not in seen_dates:
            seen_dates.add(day)
            deduped.append(row)
    deduped.reverse()                               # back to chronological order

    # Fall back to yfinance when DB has fewer than 5 distinct trading days.
    # Always use yfinance when more than 30 days are requested — the poller
    # only accumulates ~1 row/day so the DB won't have enough for SMA-50/200
    # until the app has been running for months.
    if len(deduped) >= 5 and days <= 35:
        return deduped

    # Fetch directly from yfinance for longer ranges or sparse DB
    live = fetch_ohlcv(symbol, exchange.upper(), days=days)
    return [
        OHLCVOut(
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        for bar in live
    ]


# ── WebSocket — live price push ───────────────────────────────────────────────

_IST_OFFSET = timedelta(hours=5, minutes=30)


def _ist_now() -> datetime:
    """Current time as a naive datetime in IST."""
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)


def _is_market_open() -> bool:
    """True during NSE/BSE trading hours: Mon–Fri 09:15–15:30 IST."""
    now = _ist_now()
    if now.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    t = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= t < 15 * 60 + 30


def _seconds_until_next_market_open() -> float:
    """
    Seconds from now (IST) until the next 09:15 IST on a weekday.
    Capped at 24 h so we re-evaluate at most once per day.
    """
    now = _ist_now()
    # Start from tomorrow if we're past 09:15 today (or it's already closed)
    candidate = now.replace(hour=9, minute=15, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    # Skip weekends
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    secs = (candidate - now).total_seconds()
    return min(secs, 86_400)   # cap at 24 h


@router.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    """
    Push latest prices for all watchlist symbols via WebSocket.

    Cadence:
      • Always sends one push immediately on connect (cold-start snapshot).
      • During market hours (IST 09:15–15:30, Mon–Fri): pushes every 60 s.
      • Outside market hours: after the initial push, sleeps until the next
        09:15 IST open, sends one push, then switches to 60 s cadence.
        This avoids broadcasting the same stale numbers thousands of times
        over a weekend while keeping the connection alive.

    Serves entirely from the in-process quote cache — zero yfinance calls.
    """
    await websocket.accept()

    def _push_payload() -> list[dict]:
        return [
            {"symbol": q.symbol, "exchange": q.exchange,
             "ltp": q.ltp, "pct_change": q.pct_change}
            for q in get_all_cached_quotes()
        ]

    async def _interruptible_sleep(total_secs: float, chunk: float = 5.0) -> None:
        """Sleep in small chunks so CancelledError fires within `chunk` seconds."""
        remaining = total_secs
        while remaining > 0:
            await asyncio.sleep(min(chunk, remaining))
            remaining -= chunk

    try:
        # ── Initial push — always sent immediately on connect ─────────────────
        await websocket.send_json(_push_payload())

        while True:
            if _is_market_open():
                # Market hours: tick every 60 s
                await _interruptible_sleep(60)
                await websocket.send_json(_push_payload())
            else:
                # Off-hours: sleep until next open, then send one wakeup push
                sleep_secs = _seconds_until_next_market_open()
                await _interruptible_sleep(sleep_secs)
                await websocket.send_json(_push_payload())
                # Now we're at market open — fall through to 60 s loop next iter

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
