"""
Unified market data fetcher — uses yfinance for both NSE and BSE quotes.

Symbol search uses NSE's public equity master CSV (EQUITY_L.csv), downloaded
once on first call and cached in memory for the lifetime of the process.

Public API
----------
  fetch_quote(symbol, exchange)  →  QuoteResult | None
  search_symbols(query)          →  list[SymbolInfo]
"""
from __future__ import annotations

import csv
import io
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import requests
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


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class OHLCVResult:
    timestamp: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None


# ── Main fetch functions ──────────────────────────────────────────────────────

def fetch_ohlcv(symbol: str, exchange: str, days: int = 30) -> list[OHLCVResult]:
    """
    Fetch daily OHLCV bars for the last `days` calendar days via yfinance.
    Returns an empty list on any failure.
    """
    if not YF_AVAILABLE:
        return []

    exchange = exchange.upper()
    suffixes = [".NS"] if exchange == "NSE" else [".BO", ".NS"]
    if symbol.isdigit() and exchange == "NSE":
        suffixes = [".NS", ".BO"]

    end_dt   = datetime.now()
    # Add a small buffer so the last trading day is always included
    start_dt = end_dt - timedelta(days=days + 7)

    for suffix in suffixes:
        ticker_str = f"{symbol}{suffix}"
        try:
            ticker = yf.Ticker(ticker_str)
            hist = ticker.history(
                start=start_dt.strftime("%Y-%m-%d"),
                end=end_dt.strftime("%Y-%m-%d"),
                interval="1d",
            )
            if hist.empty:
                continue
            results: list[OHLCVResult] = []
            for ts, row in hist.iterrows():
                # ts is a pandas Timestamp (tz-aware); convert to naive UTC datetime
                naive_dt = ts.to_pydatetime().replace(tzinfo=None)
                results.append(OHLCVResult(
                    timestamp=naive_dt,
                    open=float(row["Open"])   if row["Open"]   == row["Open"] else None,
                    high=float(row["High"])   if row["High"]   == row["High"] else None,
                    low=float(row["Low"])     if row["Low"]    == row["Low"]  else None,
                    close=float(row["Close"]),
                    volume=int(row["Volume"]) if row["Volume"] == row["Volume"] else None,
                ))
            return results
        except Exception as exc:
            logger.debug(f"fetch_ohlcv failed for {ticker_str}: {exc}")

    logger.warning(f"No OHLCV data from yfinance for {symbol}/{exchange}")
    return []


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


# ── NSE symbol master — downloaded once, searched in memory ──────────────────

_nse_symbols: list[dict] = []          # [{symbol, name}]
_nse_load_lock = threading.Lock()
_nse_loaded = False

_NSE_CSV_URL = (
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
)


def _ensure_nse_symbols() -> None:
    """Download and cache the NSE equity master list (runs at most once)."""
    global _nse_symbols, _nse_loaded
    if _nse_loaded:
        return
    with _nse_load_lock:
        if _nse_loaded:          # double-check after acquiring lock
            return
        try:
            resp = requests.get(
                _NSE_CSV_URL,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            reader = csv.DictReader(io.StringIO(resp.text))
            _nse_symbols = [
                {
                    "symbol": row["SYMBOL"].strip(),
                    "name":   row["NAME OF COMPANY"].strip(),
                    "isin":   row[" ISIN NUMBER"].strip(),
                }
                for row in reader
                if row.get("SYMBOL") and row.get(" SERIES", "").strip() == "EQ"
            ]
            _nse_loaded = True
            logger.info(f"NSE equity master loaded: {len(_nse_symbols)} symbols")
        except Exception as exc:
            logger.warning(f"Could not load NSE equity master: {exc}")


def search_symbols(query: str) -> list[SymbolInfo]:
    """
    Search NSE equity master by symbol or company name.
    Returns up to 10 matches, ranked: exact symbol prefix first, then name matches.
    """
    if not query or len(query) < 1:
        return []

    _ensure_nse_symbols()

    q = query.strip().upper()
    exact:   list[SymbolInfo] = []
    partial: list[SymbolInfo] = []

    for row in _nse_symbols:
        sym  = row["symbol"].upper()
        name = row["name"].upper()
        info = SymbolInfo(
            symbol=row["symbol"],
            exchange="NSE",
            company_name=row["name"],
        )
        if sym == q or sym.startswith(q):
            exact.append(info)
        elif q in sym or q in name:
            partial.append(info)

    return (exact + partial)[:10]


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



# ── News headlines ────────────────────────────────────────────────────────────

@dataclass
class NewsItem:
    title: str
    summary: str
    publisher: str
    published_at: str   # ISO-8601 string


def fetch_news(symbol: str, exchange: str, max_items: int = 5) -> list[NewsItem]:
    """
    Fetch recent news headlines for a symbol via yfinance.
    Returns up to `max_items` items; returns [] on any failure.
    The new yfinance news structure nests data under item['content'].
    """
    if not YF_AVAILABLE:
        return []

    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    try:
        ticker = yf.Ticker(f"{symbol}{suffix}")
        raw = ticker.news or []
        items: list[NewsItem] = []
        for entry in raw[:max_items]:
            c = entry.get("content", {}) or {}
            title = c.get("title", "").strip()
            if not title:
                continue
            summary   = (c.get("summary") or c.get("description") or "").strip()
            publisher = (c.get("provider") or {}).get("displayName", "")
            pub_date  = c.get("pubDate") or c.get("displayTime") or ""
            items.append(NewsItem(
                title=title,
                summary=summary[:300],   # cap length
                publisher=publisher,
                published_at=pub_date[:10],   # keep YYYY-MM-DD
            ))
        return items
    except Exception as exc:
        logger.debug(f"fetch_news failed for {symbol}/{exchange}: {exc}")
        return []


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
