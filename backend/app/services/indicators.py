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
from backend.app.services.data_fetch import fetch_ohlcv


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
    sma_200: float | None = None
    ema_20: float | None = None
    rsi_14: float | None = None
    realized_volatility_30d: float | None = None   # annualised std of daily returns
    price_vs_sma20_pct: float | None = None        # how far above/below 20-day SMA
    enough_history: bool = False                   # False when < 20 candles available
    signal_context: str = ""                       # human-readable deterministic signals
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "errors"}


# ── Main function ─────────────────────────────────────────────────────────────

def compute_indicators(symbol: str, exchange: str, db: Session) -> IndicatorSnapshot:
    """
    Load price_history from the DB and compute all indicators.
    Falls back to yfinance OHLCV when DB has fewer than 20 rows (not enough
    for SMA-20 / RSI-14).  Always returns an IndicatorSnapshot — individual
    fields may be None if insufficient history, but will never raise.
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

    # Need at least 200 rows for SMA-200; always fetch 300 calendar days from
    # yfinance (~212 trading bars) so SMA-50 and SMA-200 are always available.
    if len(rows) < 200:
        logger.info(
            f"compute_indicators: DB has {len(rows)} rows for {symbol} — "
            "fetching 300-day history from yfinance"
        )
        yf_bars = fetch_ohlcv(symbol, exchange, days=300)
        if yf_bars:
            closes = pd.Series([b.close for b in yf_bars], dtype=float)
        elif rows:
            closes = pd.Series([r.close for r in rows], dtype=float)
        else:
            snap.errors.append("No price history found in DB or yfinance")
            return snap
    else:
        closes = pd.Series([r.close for r in rows], dtype=float)

    if closes.empty:
        snap.errors.append("No price history found")
        return snap
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
        snap.sma_50  = round(float(closes.rolling(50).mean().iloc[-1]),  2)
    if n >= 200:
        snap.sma_200 = round(float(closes.rolling(200).mean().iloc[-1]), 2)

    # ── RSI (14-period) ───────────────────────────────────────────────────────
    if n >= 15:
        snap.rsi_14 = round(_rsi(closes, period=14), 2)

    # ── Realized volatility (30-day annualised) ───────────────────────────────
    if n >= 31:
        log_returns = closes.pct_change().dropna()[-30:]
        snap.realized_volatility_30d = round(
            float(log_returns.std() * (252 ** 0.5) * 100), 2
        )  # expressed as %

    # ── Deterministic signal context ─────────────────────────────────────────
    snap.signal_context = _build_signal_context(snap)

    return snap


def _build_signal_context(snap: IndicatorSnapshot) -> str:
    """
    Derive plain-language trading signals purely from computed indicators.
    These are deterministic rules — the LLM interprets them, never computes them.
    """
    signals: list[str] = []

    rsi  = snap.rsi_14
    p    = snap.current_price
    s20  = snap.sma_20
    e20  = snap.ema_20
    s50  = snap.sma_50
    s200 = snap.sma_200
    vol  = snap.realized_volatility_30d
    vs20 = snap.price_vs_sma20_pct

    # ── RSI signals ──────────────────────────────────────────────────────────
    if rsi is not None:
        if rsi < 30:
            signals.append(f"RSI is {rsi:.1f} — strongly oversold (below 30); historically a mean-reversion watch zone.")
        elif rsi < 40:
            signals.append(f"RSI is {rsi:.1f} — mildly oversold (30–40); weakening momentum.")
        elif rsi > 70:
            signals.append(f"RSI is {rsi:.1f} — overbought (above 70); watch for a pullback.")
        elif rsi > 60:
            signals.append(f"RSI is {rsi:.1f} — approaching overbought territory (60–70).")
        else:
            signals.append(f"RSI is {rsi:.1f} — neutral zone (40–60).")

    # ── Price vs moving averages ──────────────────────────────────────────────
    if p and s20:
        if vs20 is not None:
            rel = f"{vs20:+.2f}%"
            if p > s20:
                signals.append(f"Price ({p:.2f}) is ABOVE SMA-20 ({s20:.2f}) by {rel} — short-term uptrend.")
            else:
                signals.append(f"Price ({p:.2f}) is BELOW SMA-20 ({s20:.2f}) by {rel} — short-term downtrend.")

    if p and e20:
        if p > e20:
            signals.append(f"Price is above EMA-20 ({e20:.2f}) — bullish short-term momentum.")
        else:
            signals.append(f"Price is below EMA-20 ({e20:.2f}) — bearish short-term momentum.")

    if p and s50:
        if p > s50:
            signals.append(f"Price is above DMA-50 ({s50:.2f}) — medium-term trend is UP.")
        else:
            signals.append(f"Price is below DMA-50 ({s50:.2f}) — medium-term trend is DOWN.")

    if p and s200:
        if p > s200:
            signals.append(f"Price is above DMA-200 ({s200:.2f}) — long-term trend is BULLISH.")
        else:
            signals.append(f"Price is below DMA-200 ({s200:.2f}) — long-term trend is BEARISH.")

    # ── SMA-20 / DMA-50 crossover (golden/death cross approximation) ─────────
    if s20 and s50:
        if s20 > s50:
            signals.append("SMA-20 > DMA-50 — bullish alignment (short-term average above medium-term).")
        else:
            signals.append("SMA-20 < DMA-50 — bearish alignment (short-term average below medium-term).")

    # ── DMA-50 / DMA-200 golden/death cross ───────────────────────────────────
    if s50 and s200:
        if s50 > s200:
            signals.append(f"DMA-50 ({s50:.2f}) > DMA-200 ({s200:.2f}) — GOLDEN CROSS: long-term bullish signal.")
        else:
            signals.append(f"DMA-50 ({s50:.2f}) < DMA-200 ({s200:.2f}) — DEATH CROSS: long-term bearish signal.")

    # ── Volatility context ────────────────────────────────────────────────────
    if vol is not None:
        if vol > 35:
            signals.append(f"Annualised volatility is HIGH at {vol:.1f}% — elevated risk; position sizing caution advised.")
        elif vol > 20:
            signals.append(f"Annualised volatility is MODERATE at {vol:.1f}%.")
        else:
            signals.append(f"Annualised volatility is LOW at {vol:.1f}% — relatively stable price action.")

    # ── Trend summary ─────────────────────────────────────────────────────────
    bullish = sum([
        bool(rsi is not None and rsi < 50),
        bool(p and s20 and p > s20),
        bool(p and e20 and p > e20),
        bool(p and s50 and p > s50),
        bool(p and s200 and p > s200),
    ])
    bearish = sum([
        bool(rsi is not None and rsi > 50),
        bool(p and s20 and p < s20),
        bool(p and e20 and p < e20),
        bool(p and s50 and p < s50),
        bool(p and s200 and p < s200),
    ])
    if bullish > bearish:
        signals.append("OVERALL SIGNAL: More bullish signals than bearish based on available indicators.")
    elif bearish > bullish:
        signals.append("OVERALL SIGNAL: More bearish signals than bullish based on available indicators.")
    else:
        signals.append("OVERALL SIGNAL: Mixed — bullish and bearish signals roughly balanced.")

    return "\n".join(f"- {s}" for s in signals) if signals else "Insufficient data for signal generation."


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
