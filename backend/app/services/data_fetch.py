"""
Unified market data fetcher — uses yfinance for both NSE and BSE quotes.

nsepython / bsedata are no longer used as primary sources because:
  - NSE's website now requires a live browser session (blocks server-side requests → 403)
  - bsedata scrip-code lookups are unreliable on yfinance's .BO feed

yfinance ticker conventions used here:
  NSE  →  {SYMBOL}.NS   e.g. RELIANCE.NS, AXISBANK.NS
  BSE  →  {SYMBOL}.BO   e.g. RELIANCE.BO  (or fall back to .NS if .BO has no data)

For BSE scrip-code entries (e.g. "500325") yfinance does not work well —
the code attempts a .BO lookup and, if empty, falls back to a .NS lookup so
mixed watchlists still work.

Public API
----------
  fetch_quote(symbol, exchange)  →  QuoteResult | None
  search_symbols(query)          →  list[SymbolInfo]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception:  # pragma: no cover
    YF_AVAILABLE = False
    logger.warning("yfinance not available — all price fetches will fail")


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class QuoteResult:
    symbol: str
    exchange: str
    company_name: str
    ltp: float              # Last Traded Price
    open: float | None
    high: float | None
    low: float | None
    prev_close: float | None
    volume: int | None
    pct_change: float | None


@dataclass
class SymbolInfo:
    symbol: str
    exchange: str
    company_name: str
    sector: str | None = None


# ── Main fetch functions ──────────────────────────────────────────────────────

def fetch_quote(symbol: str, exchange: str) -> Optional[QuoteResult]:
    """
    Fetch a live quote for the given symbol on the given exchange via yfinance.

    Parameters
    ----------
    symbol   : NSE trading symbol (e.g. "RELIANCE") or BSE scrip/symbol (e.g. "500325").
    exchange : "NSE" or "BSE" (case-insensitive).

    Returns None on any failure so callers can decide how to handle gaps.
    """
    if not YF_AVAILABLE:
        return None

    exchange = exchange.upper()
    try:
        if exchange == "BSE":
            return _fetch_yf_quote(symbol, "BSE")
        else:
            return _fetch_yf_quote(symbol, "NSE")
    except Exception as exc:
        logger.error(f"fetch_quote failed for {symbol}/{exchange}: {exc}")
        return None


def search_symbols(query: str) -> list[SymbolInfo]:
    """
    Search for symbols by name or ticker.
    yfinance doesn't offer a free-text search API, so this returns an empty
    list — the frontend should let users type known symbols directly.
    """
    return []


# ── Internal helpers ──────────────────────────────────────────────────────────

def _fetch_yf_quote(symbol: str, exchange: str) -> Optional[QuoteResult]:
    """
    Fetch a quote using yfinance.

    Ticker suffix strategy:
      NSE  → try {symbol}.NS; if it looks like a BSE scrip code (all digits)
             also try {symbol}.BO as fallback
      BSE  → try {symbol}.BO first; fall back to {symbol}.NS
             (BSE scrip codes like "500325" are often unavailable on .BO feed)
    """
    if exchange == "NSE":
        # Numeric-only symbols are BSE scrip codes accidentally stored as NSE.
        # Try .NS first; if that yields nothing and the symbol is all digits,
        # also attempt .BO so the user doesn't see a blank row.
        suffixes = [".NS", ".BO"] if symbol.isdigit() else [".NS"]
    else:
        suffixes = [".BO", ".NS"]

    for suffix in suffixes:
        ticker_str = f"{symbol}{suffix}"
        result = _yf_ticker_quote(ticker_str, symbol, exchange)
        if result is not None:
            return result

    logger.warning(f"No data returned from yfinance for {symbol}/{exchange}")
    return None


def _yf_ticker_quote(ticker_str: str, symbol: str, exchange: str) -> Optional[QuoteResult]:
    """Call yfinance for one ticker string and map to QuoteResult."""
    try:
        ticker = yf.Ticker(ticker_str)

        # fast_info is the lightweight path — no heavy info dict download
        fi = ticker.fast_info

        ltp = _safe_float(fi.last_price)
        if ltp is None or ltp == 0:
            return None

        prev_close = _safe_float(fi.previous_close)
        pct_change: float | None = None
        if ltp and prev_close and prev_close != 0:
            pct_change = round((ltp - prev_close) / prev_close * 100, 2)

        # Company name — only fetched when fast_info succeeds (cached by yfinance)
        company_name = ""
        try:
            company_name = ticker.info.get("longName") or ticker.info.get("shortName") or ""
        except Exception:
            pass

        return QuoteResult(
            symbol=symbol,
            exchange=exchange,
            company_name=company_name,
            ltp=ltp,
            open=_safe_float(fi.open),
            high=_safe_float(fi.day_high),
            low=_safe_float(fi.day_low),
            prev_close=prev_close,
            volume=_safe_int(fi.three_month_average_volume),
            pct_change=pct_change,
        )
    except Exception as exc:
        logger.debug(f"yfinance lookup failed for {ticker_str}: {exc}")
        return None


# ── Utilities ─────────────────────────────────────────────────────────────────

def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        # yfinance returns NaN for missing fields
        import math
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> int | None:
    try:
        if value is None:
            return None
        import math
        f = float(value)
        return None if math.isnan(f) else int(f)
    except (ValueError, TypeError):
        return None
