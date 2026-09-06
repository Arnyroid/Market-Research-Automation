"""
Prices router — latest quotes, OHLCV history, and a WebSocket push channel.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.db import SessionLocal, get_db
from backend.app.models import PriceHistory, Watchlist
from backend.app.services.data_fetch import fetch_ohlcv, fetch_quote

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

@router.get("/{symbol}", response_model=QuoteOut)
def get_quote(symbol: str, exchange: str = "NSE"):
    """Fetch a live quote (bypasses DB, calls exchange API directly)."""
    quote = fetch_quote(symbol, exchange.upper())
    if quote is None:
        raise HTTPException(status_code=503, detail="Could not fetch quote — exchange API unavailable")
    return QuoteOut(
        symbol=quote.symbol,
        exchange=quote.exchange,
        company_name=quote.company_name or None,
        ltp=quote.ltp,
        open=quote.open,
        high=quote.high,
        low=quote.low,
        prev_close=quote.prev_close,
        volume=quote.volume,
        pct_change=quote.pct_change,
    )


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

@router.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    """
    Push latest prices for all watchlist symbols every 60 seconds.
    The frontend connects once and receives periodic JSON updates.
    """
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                symbols = db.query(Watchlist).all()
            finally:
                db.close()

            payload: list[dict] = []
            for item in symbols:
                quote = fetch_quote(item.symbol, item.exchange)
                if quote:
                    payload.append({
                        "symbol": quote.symbol,
                        "exchange": quote.exchange,
                        "ltp": quote.ltp,
                        "pct_change": quote.pct_change,
                    })

            await websocket.send_json(payload)
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
