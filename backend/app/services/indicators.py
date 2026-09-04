"""
Technical indicators service.

All computations are deterministic Python/pandas — the LLM is never
asked to compute numbers, only to interpret them.

Public API
----------
  compute_indicators(symbol, exchange, db)  →  IndicatorSnapshot
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from backend.app.models import PriceHistory


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class IndicatorSnapshot:
    symbol: str
    exchange: str
    current_price: float | None = None
    prev_close: float | None = None
    pct_change_1d: float | None = None
    pct_change_5d: float | None = None
    pct_change_30d: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    ema_20: float | None = None
    rsi_14: float | None = None
    realized_volatility_30d: float | None = None   # annualised std of daily returns
    price_vs_sma20_pct: float | None = None        # how far above/below 20-day SMA
    enough_history: bool = False                   # False when < 20 candles available
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "errors"}


# ── Main function ─────────────────────────────────────────────────────────────

def compute_indicators(symbol: str, exchange: str, db: Session) -> IndicatorSnapshot:
    """
    Load price_history from the DB and compute all indicators.
    Always returns an IndicatorSnapshot — individual fields may be None if
    there is insufficient history, but will never raise.
    """
    snap = IndicatorSnapshot(symbol=symbol, exchange=exchange)

    rows = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.symbol == symbol,
            PriceHistory.exchange == exchange,
        )
        .order_by(PriceHistory.timestamp.asc())
        .all()
    )

    if not rows:
        snap.errors.append("No price history found")
        return snap

    closes = pd.Series([r.close for r in rows], dtype=float)
    n = len(closes)

    snap.current_price = float(closes.iloc[-1])
    snap.enough_history = n >= 20

    # ── Simple % changes ─────────────────────────────────────────────────────
    if n >= 2:
        snap.prev_close = float(closes.iloc[-2])
        snap.pct_change_1d = _pct(closes.iloc[-1], closes.iloc[-2])
    if n >= 6:
        snap.pct_change_5d = _pct(closes.iloc[-1], closes.iloc[-6])
    if n >= 31:
        snap.pct_change_30d = _pct(closes.iloc[-1], closes.iloc[-31])

    # ── Moving averages ───────────────────────────────────────────────────────
    if n >= 20:
        snap.sma_20 = round(float(closes.rolling(20).mean().iloc[-1]), 2)
        snap.ema_20 = round(float(closes.ewm(span=20, adjust=False).mean().iloc[-1]), 2)
        if snap.current_price and snap.sma_20:
            snap.price_vs_sma20_pct = _pct(snap.current_price, snap.sma_20)

    if n >= 50:
        snap.sma_50 = round(float(closes.rolling(50).mean().iloc[-1]), 2)

    # ── RSI (14-period) ───────────────────────────────────────────────────────
    if n >= 15:
        snap.rsi_14 = round(_rsi(closes, period=14), 2)

    # ── Realized volatility (30-day annualised) ───────────────────────────────
    if n >= 31:
        log_returns = closes.pct_change().dropna()[-30:]
        snap.realized_volatility_30d = round(
            float(log_returns.std() * (252 ** 0.5) * 100), 2
        )  # expressed as %

    return snap


# ── Internal helpers ──────────────────────────────────────────────────────────

def _pct(current: float, base: float) -> float | None:
    if base == 0:
        return None
    return round((current - base) / base * 100, 2)


def _rsi(closes: pd.Series, period: int = 14) -> float:
    """Wilder's RSI."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # First averages
    avg_gain = gain.iloc[1:period + 1].mean()
    avg_loss = loss.iloc[1:period + 1].mean()

    # Wilder smoothing over the rest
    for price_gain, price_loss in zip(gain.iloc[period + 1:], loss.iloc[period + 1:]):
        avg_gain = (avg_gain * (period - 1) + price_gain) / period
        avg_loss = (avg_loss * (period - 1) + price_loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
