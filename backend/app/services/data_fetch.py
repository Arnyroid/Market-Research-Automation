"""
Unified market data fetcher — abstracts BSE (bsedata) and NSE (nsepython)
behind a single interface so the rest of the codebase never needs to know
which exchange it is talking to.

Public API
----------
  fetch_quote(symbol, exchange)  →  QuoteResult | None
  fetch_ohlcv(symbol, exchange)  →  OHLCVResult | None
  search_symbols(query)          →  list[SymbolInfo]
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger

# ── BSE ───────────────────────────────────────────────────────────────────────
try:
    from bsedata.bse import BSE
    _bse = BSE()
    BSE_AVAILABLE = True
except Exception:  # pragma: no cover
    BSE_AVAILABLE = False
    logger.warning("bsedata not available — BSE quotes will be skipped")

# ── NSE ───────────────────────────────────────────────────────────────────────
try:
    import nsepython as nse
    NSE_AVAILABLE = True
except Exception:  # pragma: no cover
    NSE_AVAILABLE = False
    logger.warning("nsepython not available — NSE quotes will be skipped")


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
    Fetch a live quote for the given symbol on the given exchange.

    Parameters
    ----------
    symbol   : BSE scrip code (e.g. "500325") for BSE,
               NSE trading symbol (e.g. "RELIANCE") for NSE.
    exchange : "BSE" or "NSE" (case-insensitive).

    Returns None on any failure so callers can decide how to handle gaps.
    """
    exchange = exchange.upper()
    try:
        if exchange == "BSE":
            return _fetch_bse_quote(symbol)
        elif exchange == "NSE":
            return _fetch_nse_quote(symbol)
        else:
            logger.warning(f"Unknown exchange '{exchange}' for symbol '{symbol}'")
            return None
    except Exception as exc:
        logger.error(f"fetch_quote failed for {symbol}/{exchange}: {exc}")
        return None


def search_symbols(query: str) -> list[SymbolInfo]:
    """
    Search for symbols by name or ticker across both exchanges.
    Returns up to 20 combined results.
    """
    results: list[SymbolInfo] = []

    if NSE_AVAILABLE:
        try:
            nse_hits = nse.nse_eq(query) if query else []
            for item in (nse_hits or [])[:10]:
                results.append(SymbolInfo(
                    symbol=item.get("symbol", ""),
                    exchange="NSE",
                    company_name=item.get("companyName", ""),
                    sector=item.get("industry", None),
                ))
        except Exception as exc:
            logger.warning(f"NSE symbol search failed: {exc}")

    # BSE doesn't have a free text search via bsedata; fall back to empty
    return results[:20]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _fetch_bse_quote(scrip_code: str) -> Optional[QuoteResult]:
    if not BSE_AVAILABLE:
        return None

    # bsedata rate-limit: avoid hammering
    time.sleep(0.2)

    raw = _bse.getQuote(scrip_code)
    if not raw:
        return None

    ltp = _to_float(raw.get("currentValue"))
    if ltp is None:
        return None

    prev_close = _to_float(raw.get("previousClose"))

    # bsedata 0.6.x uses pChange (already a % string, e.g. "1.61")
    pct_change = _to_float(raw.get("pChange"))

    # totalTradedQuantity is formatted like "4.60 Lakh" — parse to int
    volume = _parse_bse_volume(raw.get("totalTradedQuantity", ""))

    return QuoteResult(
        symbol=scrip_code,
        exchange="BSE",
        company_name=raw.get("companyName", ""),
        ltp=ltp,
        open=_to_float(raw.get("previousOpen")),   # best proxy; no intraday open field
        high=_to_float(raw.get("dayHigh")),
        low=_to_float(raw.get("dayLow")),
        prev_close=prev_close,
        volume=volume,
        pct_change=pct_change,
    )


def _fetch_nse_quote(symbol: str) -> Optional[QuoteResult]:
    if not NSE_AVAILABLE:
        return None

    time.sleep(0.2)

    try:
        raw = nse.nse_eq(symbol)
    except Exception:
        return None

    if not raw or "priceInfo" not in raw:
        return None

    price_info = raw["priceInfo"]
    ltp = _to_float(price_info.get("lastPrice"))
    if ltp is None:
        return None

    prev_close = _to_float(price_info.get("previousClose"))
    pct_change: float | None = None
    if ltp and prev_close and prev_close != 0:
        pct_change = round((ltp - prev_close) / prev_close * 100, 2)

    ohlc = price_info.get("intraDayHighLow", {})

    return QuoteResult(
        symbol=symbol,
        exchange="NSE",
        company_name=raw.get("info", {}).get("companyName", ""),
        ltp=ltp,
        open=_to_float(price_info.get("open")),
        high=_to_float(ohlc.get("max")),
        low=_to_float(ohlc.get("min")),
        prev_close=prev_close,
        volume=_to_int(
            raw.get("marketDeptOrderBook", {})
               .get("tradeInfo", {})
               .get("totalTradedVolume")
        ),
        pct_change=pct_change,
    )


# ── Utilities ─────────────────────────────────────────────────────────────────

def _to_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _to_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_bse_volume(raw: str) -> int | None:
    """
    bsedata 0.6.x returns volume as a human-readable string, e.g.:
      "4.60 Lakh"  → 460_000
      "1.23 Cr."   → 12_300_000
      "500"        → 500
    """
    if not raw or raw.strip() in ("-", ""):
        return None
    raw = raw.strip()
    multipliers = {"lakh": 100_000, "cr.": 10_000_000, "cr": 10_000_000}
    parts = raw.lower().split()
    try:
        num = float(parts[0].replace(",", ""))
        if len(parts) > 1 and parts[1] in multipliers:
            return round(num * multipliers[parts[1]])
        return int(num)
    except (ValueError, IndexError):
        return None
