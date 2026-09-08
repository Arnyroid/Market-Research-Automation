"""
Unified market data fetcher — uses yfinance for both NSE and BSE quotes.

Symbol search uses NSE's public equity master CSV (EQUITY_L.csv), downloaded
once on first call and cached in memory for the lifetime of the process.

Public API
----------
  fetch_quote(symbol, exchange)       →  QuoteResult | None
  search_symbols(query)               →  list[SymbolInfo]
  fetch_fundamentals(symbol)          →  FundamentalsResult | None   (24h cached)
"""
from __future__ import annotations

import csv
import io
import re as _re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
from loguru import logger


# ── In-process quote cache ────────────────────────────────────────────────────
# Keyed by "SYMBOL:EXCHANGE" (upper-case).
# Written by the price poller (and on individual fetch_quote calls).
# Read by /prices/batch, /prices/{symbol}, and the WebSocket push.
# This means page loads serve instantly from cache — no yfinance on every request.

@dataclass
class _CachedQuote:
    result:    "QuoteResult"
    fetched_at: datetime


_quote_cache: dict[str, _CachedQuote] = {}
_quote_cache_lock = threading.Lock()

# Cache TTL:
#   During market hours the poller refreshes every N minutes, so reads are
#   always fresh.  Outside market hours prices don't change — serve cache
#   indefinitely until next market open (24h cap to handle weekend rollovers).
_QUOTE_CACHE_TTL_MARKET   = timedelta(minutes=10)   # stale after 10 min during hours
_QUOTE_CACHE_TTL_OFFHOURS = timedelta(hours=24)     # fine to hold overnight / weekends


def _cache_key(symbol: str, exchange: str) -> str:
    return f"{symbol.upper()}:{exchange.upper()}"


def cache_quote(result: "QuoteResult") -> None:
    """Write a QuoteResult into the in-process cache. Called by the poller."""
    key = _cache_key(result.symbol, result.exchange)
    with _quote_cache_lock:
        _quote_cache[key] = _CachedQuote(result=result, fetched_at=datetime.utcnow())


def get_cached_quote(symbol: str, exchange: str) -> "QuoteResult | None":
    """
    Return a cached quote if it exists and is not stale, else None.
    Staleness depends on whether we are currently in market hours.
    """
    key = _cache_key(symbol, exchange)
    with _quote_cache_lock:
        entry = _quote_cache.get(key)
    if entry is None:
        return None
    age = datetime.utcnow() - entry.fetched_at
    # Simple market-hours check in UTC: IST 9:15–15:30 = UTC 3:45–10:00
    now_utc_hm = datetime.utcnow().strftime("%H:%M")
    in_market = "03:45" <= now_utc_hm <= "10:00"
    ttl = _QUOTE_CACHE_TTL_MARKET if in_market else _QUOTE_CACHE_TTL_OFFHOURS
    if age > ttl:
        return None
    return entry.result


def get_all_cached_quotes() -> list["QuoteResult"]:
    """Return all currently valid cached quotes (used by WebSocket push)."""
    now = datetime.utcnow()
    now_utc_hm = now.strftime("%H:%M")
    in_market = "03:45" <= now_utc_hm <= "10:00"
    ttl = _QUOTE_CACHE_TTL_MARKET if in_market else _QUOTE_CACHE_TTL_OFFHOURS
    with _quote_cache_lock:
        return [
            e.result for e in _quote_cache.values()
            if (now - e.fetched_at) <= ttl
        ]

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
    Result is written into the in-process quote cache on success.

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
        result = _fetch_yf_quote(symbol, exchange)
        if result is not None:
            cache_quote(result)
        return result
    except Exception as exc:
        logger.error(f"fetch_quote failed for {symbol}/{exchange}: {exc}")
        return None


# ── NSE symbol master — downloaded once, searched in memory ──────────────────

_nse_symbols: list[dict] = []          # [{symbol, name, isin}]
_nse_load_lock = threading.Lock()
_nse_loaded = False

_NSE_CSV_URL = (
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
)

# ── BSE symbol master — downloaded once, searched in memory ──────────────────
# BSE scrip master: SecurityId (NSE-style symbol), SecurityName, ScripCode (6-digit), ISIN
# Columns: Exchange,SecurityCode,SecurityId,SecurityName,Status,GroupName,FaceValue,ISINNo

_bse_symbols: list[dict] = []          # [{symbol, name, scrip_code, isin}]
_bse_load_lock = threading.Lock()
_bse_loaded = False

_BSE_CSV_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&Status=Active"
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


def _ensure_bse_symbols() -> None:
    """
    Download and cache the BSE equity scrip master (runs at most once).
    BSE returns a JSON array from their API.  Each element has:
      SCRIP_CD  → numeric scrip code (e.g. "500325")
      SCRIP_ID  → NSE-style symbol / BSE short symbol (e.g. "RELIANCE")
      SCRIP_NM  → full company name
      ISIN_CODE → ISIN
    Falls back gracefully if the endpoint is unavailable.
    """
    global _bse_symbols, _bse_loaded
    if _bse_loaded:
        return
    with _bse_load_lock:
        if _bse_loaded:
            return
        try:
            resp = requests.get(
                _BSE_CSV_URL,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://www.bseindia.com/",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            rows: list[dict] = []
            for item in data:
                sym  = (item.get("SCRIP_ID") or item.get("scrip_id") or "").strip()
                name = (item.get("SCRIP_NM") or item.get("scrip_nm") or "").strip()
                code = str(item.get("SCRIP_CD") or item.get("scrip_cd") or "").strip()
                isin = (item.get("ISIN_CODE") or item.get("isin_code") or "").strip()
                if sym and name:
                    rows.append({"symbol": sym, "name": name, "scrip_code": code, "isin": isin})
            _bse_symbols = rows
            _bse_loaded = True
            logger.info(f"BSE equity master loaded: {len(_bse_symbols)} symbols")
        except Exception as exc:
            logger.warning(f"Could not load BSE equity master (non-fatal): {exc}")
            _bse_loaded = True   # mark as attempted so we don't retry on every search


def search_symbols(query: str) -> list[SymbolInfo]:
    """
    Search NSE + BSE equity masters by symbol or company name.
    Returns up to 15 matches total (10 NSE + 5 BSE), ranked:
      exact symbol prefix first, then name matches.
    Results are deduplicated by ISIN so the same company doesn't appear twice.
    """
    if not query or len(query) < 1:
        return []

    _ensure_nse_symbols()
    _ensure_bse_symbols()

    q = query.strip().upper()
    exact:   list[SymbolInfo] = []
    partial: list[SymbolInfo] = []

    # ── NSE ───────────────────────────────────────────────────────────────────
    seen_isins: set[str] = set()
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
            seen_isins.add(row.get("isin", ""))
        elif q in sym or q in name:
            partial.append(info)
            seen_isins.add(row.get("isin", ""))

    nse_results = (exact + partial)[:10]

    # ── BSE — add unique entries not already covered by NSE ISIN match ────────
    bse_exact:   list[SymbolInfo] = []
    bse_partial: list[SymbolInfo] = []
    for row in _bse_symbols:
        isin = row.get("isin", "")
        if isin and isin in seen_isins:
            continue   # already returned via NSE
        sym  = row["symbol"].upper()
        name = row["name"].upper()
        info = SymbolInfo(
            symbol=row["symbol"],
            exchange="BSE",
            company_name=row["name"],
        )
        if sym == q or sym.startswith(q):
            bse_exact.append(info)
        elif q in sym or q in name:
            bse_partial.append(info)

    bse_results = (bse_exact + bse_partial)[:5]

    return nse_results + bse_results


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

        # Company name — skip ticker.info (slow ~500ms dict download).
        # The watchlist DB already stores company_name; the quote only needs price data.
        company_name = ""

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


# ── screener.in fundamentals ──────────────────────────────────────────────────

@dataclass
class PeerInfo:
    name: str
    symbol: str | None = None
    price: float | None = None
    pe_ratio: float | None = None
    market_cap: float | None = None
    div_yield: float | None = None
    net_profit: float | None = None
    roce: float | None = None
    sales_growth_3yr: float | None = None
    sales_growth_5yr: float | None = None
    roe_3yr: float | None = None


@dataclass
class TableSection:
    """A generic parsed table from screener.in (headers + rows of data)."""
    headers: list[str]
    rows: list[dict[str, str]]   # {header: cell_text}
    unit: str = ""               # e.g. "Figures in Rs. Crores" — extracted from <p class="sub">


@dataclass
class FundamentalsResult:
    symbol: str

    # ── Core ratios (top-ratios bar) ──────────────────────────────────────────
    pe_ratio: float | None = None
    book_value: float | None = None
    roce: float | None = None
    roe: float | None = None
    div_yield: float | None = None
    market_cap: float | None = None       # in Cr
    debt_to_equity: float | None = None
    eps: float | None = None
    face_value: float | None = None

    # ── Shareholding (latest quarter) ─────────────────────────────────────────
    promoter_pct: float | None = None
    fii_pct: float | None = None
    dii_pct: float | None = None
    public_pct: float | None = None

    # ── Trend tables (most-recent first, up to 8 quarters / 10 years) ─────────
    quarterly_results: TableSection | None = None       # Revenue, Expenses, PAT, OPM %
    profit_loss: TableSection | None = None             # Annual P&L
    balance_sheet: TableSection | None = None           # Annual BS
    cash_flow: TableSection | None = None               # Annual CF
    key_ratios: TableSection | None = None              # Annual ratios (ROE, ROCE, D/E…)

    # ── Growth rates (from compounded growth table if available) ──────────────
    sales_growth_3yr: float | None = None
    sales_growth_5yr: float | None = None
    profit_growth_3yr: float | None = None
    profit_growth_5yr: float | None = None

    # ── Quarterly OPM trend — last 4 quarters (convenience list) ─────────────
    opm_trend: list[float] = field(default_factory=list)

    # ── Industry / sector ─────────────────────────────────────────────────────
    sector: str | None = None
    industry: str | None = None

    # ── screener.in pros / cons ───────────────────────────────────────────────
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)

    # ── Peer comparison ───────────────────────────────────────────────────────
    peers: list[PeerInfo] = field(default_factory=list)
    # Median P/E across all companies in the same industry (from peers Median row)
    industry_pe_median: float | None = None
    # Total number of companies in the industry screener tracks (from "Median: N Co.")
    industry_peer_count: int | None = None

    # ── Metadata ──────────────────────────────────────────────────────────────
    fetched_at: float = field(default_factory=time.time)
    error: str | None = None


# In-process 24-hour cache: symbol (upper) → FundamentalsResult
_fundamentals_cache: dict[str, FundamentalsResult] = {}
_fundamentals_lock  = threading.Lock()

_SCREENER_BASE = "https://www.screener.in"
_SCREENER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_SCREENER_CACHE_TTL = 86_400   # 24 hours in seconds


def fetch_fundamentals(symbol: str, exchange: str = "NSE", force: bool = False) -> Optional[FundamentalsResult]:
    """
    Fetch fundamental data for an Indian equity from screener.in.

    Scrapes the company page for:
      - Key ratios (P/E, Book Value, ROCE, ROE, Div Yield, Market Cap, D/E, EPS)
      - Quarterly results (Revenue, Expenses, PAT, OPM %)
      - Annual P&L, Balance Sheet, Cash Flow
      - Key Ratios history (ROE, ROCE, D/E, etc. over 10 years)
      - Shareholding pattern (Promoter %, FII %, DII %, Public %)
      - Compounded growth rates (Sales / Profit: 3yr & 5yr)
      - Pros and Cons
    Then calls screener.in internal peer API for peer comparison with growth rates.

    Results are cached in-process for 24 hours — fundamentals don't change
    intraday and screener.in is rate-limited.

    Pass force=True to bypass the cache and re-scrape immediately.

    Returns None only if beautifulsoup4 is not installed.
    Otherwise always returns a FundamentalsResult (error field set on failure).
    """
    # Bug 4 fix: include exchange in the cache key so NSE and BSE listings for
    # the same symbol don't serve each other's cached fundamentals data.
    key = f"{symbol.upper()}:{exchange.upper()}"

    if not force:
        with _fundamentals_lock:
            cached = _fundamentals_cache.get(key)
            if cached and (time.time() - cached.fetched_at) < _SCREENER_CACHE_TTL:
                return cached

    result = _scrape_screener(symbol.upper())

    with _fundamentals_lock:
        _fundamentals_cache[key] = result
    return result


def _scrape_screener(symbol: str) -> FundamentalsResult:
    """Scrape screener.in company page + peer API. Never raises."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 not installed — fundamentals scraping disabled")
        return FundamentalsResult(symbol=symbol, error="beautifulsoup4 not installed")

    result = FundamentalsResult(symbol=symbol)

    # Try consolidated page first, fall back to standalone.
    # Some small-caps (e.g. BAIDFIN) have a consolidated URL that returns HTTP 200
    # but serves a page with all ratio <span class="number"> values blank — the
    # company does not report consolidated financials.  Detect this empty shell
    # and fall back to the standalone page.
    resp = None
    for path in [f"/company/{symbol}/consolidated/", f"/company/{symbol}/"]:
        try:
            r = requests.get(
                f"{_SCREENER_BASE}{path}",
                headers=_SCREENER_HEADERS,
                timeout=20,
            )
            if r.status_code == 404:
                continue
            if r.status_code != 200:
                r.raise_for_status()
            # Quick check: are there any non-empty number spans?
            # If the page is a blank consolidated shell, all spans will be empty.
            from bs4 import BeautifulSoup as _BS
            _quick = _BS(r.text, "lxml")
            _ul = _quick.find("ul", id="top-ratios")
            _has_data = False
            if _ul:
                for _span in _ul.find_all("span", class_="number"):
                    if _span.get_text(strip=True):
                        _has_data = True
                        break
            if _has_data:
                resp = r
                break
            # 200 but no data — keep trying next path (standalone)
            logger.debug(f"screener.in {path}: 200 but all ratio spans empty — trying standalone")
            resp = r   # keep as last resort if standalone also fails
        except Exception as exc:
            logger.warning(f"screener.in page fetch failed for {symbol}: {exc}")
            result.error = str(exc)
            return result

    if resp is None:
        result.error = f"No screener.in page found for {symbol}"
        logger.warning(result.error)
        return result

    soup = BeautifulSoup(resp.text, "lxml")

    # ── Sector / Industry ─────────────────────────────────────────────────────
    # screener.in renders #company-info links via JS — sector/industry are in
    # <p class="sub"> anchors whose hrefs follow /market/<L1>/ (sector) and
    # /market/<L1>/<L2>/ (industry sub-group) patterns.
    company_info_div = soup.find("div", id="company-info")
    for a in soup.find_all("a", href=_re.compile(r"^/market/")):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if not text:
            continue
        # Count non-empty path segments after /market/
        segments = [s for s in href.split("/") if s and s != "market"]
        if len(segments) == 1 and result.sector is None:
            result.sector = text          # e.g. /market/IN03/ → "Energy"
        elif len(segments) == 2 and result.industry is None:
            result.industry = text        # e.g. /market/IN03/IN0301/ → "Oil, Gas & Consumable Fuels"

    # ── Top ratios bar ────────────────────────────────────────────────────────
    top_ratios = soup.find("ul", id="top-ratios")
    if top_ratios:
        for li in top_ratios.find_all("li"):
            name_tag  = li.find("span", class_="name")
            value_tag = li.find("span", class_="number")
            if not name_tag or not value_tag:
                continue
            raw_name = name_tag.get_text(strip=True).lower()
            raw_val  = value_tag.get_text(strip=True)
            val = _parse_screener_number(raw_val)

            if   "market cap"      in raw_name: result.market_cap     = val
            elif "stock p/e"       in raw_name: result.pe_ratio        = val
            elif raw_name == "p/e":             result.pe_ratio        = val
            elif "book value"      in raw_name: result.book_value      = val
            elif "dividend yield"  in raw_name: result.div_yield       = val
            elif "roce"            in raw_name: result.roce            = val
            elif "roe"             in raw_name: result.roe             = val
            elif "face value"      in raw_name: result.face_value      = val
            elif "debt / equity"   in raw_name: result.debt_to_equity  = val
            elif "debt/equity"     in raw_name: result.debt_to_equity  = val
            elif "eps"             in raw_name: result.eps             = val

    # ── Pros and Cons ─────────────────────────────────────────────────────────
    pros_div = soup.find("div", class_="pros")
    if pros_div:
        result.pros = [li.get_text(strip=True) for li in pros_div.find_all("li")][:5]

    cons_div = soup.find("div", class_="cons")
    if cons_div:
        result.cons = [li.get_text(strip=True) for li in cons_div.find_all("li")][:5]

    # ── Main data sections (parse first table in each section) ────────────────
    section_map = {
        "quarters":     "quarterly_results",
        "profit-loss":  "profit_loss",
        "balance-sheet":"balance_sheet",
        "cash-flow":    "cash_flow",
        "ratios":       "key_ratios",
    }
    for section_id, attr in section_map.items():
        sec = soup.find("section", id=section_id)
        if sec:
            parsed = _parse_table_section(sec)
            if parsed:
                setattr(result, attr, parsed)

    # ── Compounded growth tables — sub-tables INSIDE profit-loss section ──────
    # screener.in embeds these as small tables after the main P&L table,
    # with the first cell being the title row (no <thead>).
    pl_sec = soup.find("section", id="profit-loss")
    if pl_sec:
        for tbl in pl_sec.find_all("table"):
            rows = tbl.find_all("tr")
            if not rows:
                continue
            title_cells = rows[0].find_all(["td", "th"])
            if not title_cells:
                continue
            title = title_cells[0].get_text(strip=True).lower()
            if "compounded sales growth" in title or "sales growth" in title:
                _parse_growth_table_rows(rows[1:], result, kind="sales")
            elif "compounded profit growth" in title or "profit growth" in title:
                _parse_growth_table_rows(rows[1:], result, kind="profit")

    # ── EPS (TTM) — last cell of 'EPS in Rs' row in the P&L table ────────────
    # IMPORTANT: the P&L table unit is "Figures in Rs. Crores" but the EPS row
    # is always expressed in plain rupees (not Crores). However, screener.in
    # sometimes shows EPS pre-multiplied by 1e5 (Lakh scale) for certain companies
    # in their consolidated view, producing absurd values like 1,181,900.
    # Safe rule: only use the P&L EPS fallback when the table unit does NOT
    # contain "Crore" (i.e., the table is in plain Rs. units already).
    # For Crore-denominated tables the top-ratios bar is the authoritative source.
    if pl_sec and result.eps is None:
        # Check the unit of this section
        sub_p = pl_sec.find("p", class_="sub")
        pl_unit = sub_p.get_text(strip=True).lower() if sub_p else ""
        if "crore" not in pl_unit and "cr." not in pl_unit:
            tbl = pl_sec.find("table")
            if tbl:
                for tr in tbl.find_all("tr"):
                    cells = tr.find_all(["td", "th"])
                    if not cells:
                        continue
                    label = cells[0].get_text(strip=True).lower()
                    if "eps" in label and "per share" not in label:
                        # Take the last non-empty numeric cell (TTM or most recent year)
                        for cell in reversed(cells[1:]):
                            val = _parse_screener_number(cell.get_text(strip=True))
                            if val is not None:
                                result.eps = val
                                break

    # ── Debt-to-Equity from Balance Sheet table ───────────────────────────────
    # screener.in doesn't include D/E directly in top-ratios for all companies;
    # compute it from Borrowings / Equity Capital (latest year).
    if result.debt_to_equity is None:
        bs_sec = soup.find("section", id="balance-sheet")
        if bs_sec:
            tbl = bs_sec.find("table")
            if tbl:
                borrowings: float | None = None
                equity_cap: float | None = None
                reserves:   float | None = None
                for tr in tbl.find_all("tr"):
                    cells = tr.find_all(["td", "th"])
                    if not cells:
                        continue
                    label = cells[0].get_text(strip=True).lower()
                    # Take the most recent year (last non-empty cell)
                    vals = [_parse_screener_number(c.get_text(strip=True)) for c in cells[1:]]
                    numeric = [v for v in vals if v is not None]
                    if not numeric:
                        continue
                    latest = numeric[-1]
                    if "borrow" in label:
                        borrowings = latest
                    elif "equity capital" in label or "share capital" in label:
                        equity_cap = latest
                    elif "reserve" in label:
                        reserves   = latest
                total_equity = (equity_cap or 0) + (reserves or 0)
                if borrowings is not None and total_equity > 0:
                    result.debt_to_equity = round(borrowings / total_equity, 2)

    # ── Convenience: quarterly OPM trend ──────────────────────────────────────
    if result.quarterly_results:
        result.opm_trend = _extract_opm_from_table(result.quarterly_results)

    # ── Shareholding ──────────────────────────────────────────────────────────
    sh_sec = soup.find("section", id="shareholding")
    if sh_sec:
        _extract_shareholding(sh_sec, result)

    # ── Peers + industry median PE ────────────────────────────────────────────
    if company_info_div:
        warehouse_id = company_info_div.get("data-warehouse-id")
        if warehouse_id:
            _fetch_peers_into(warehouse_id, result)

    logger.info(f"screener.in fundamentals fetched for {symbol}")
    return result


# ── Table parsers ─────────────────────────────────────────────────────────────

def _parse_table_section(section) -> TableSection | None:
    """
    Parse a screener.in data section that contains a single <table>.
    Returns a TableSection with headers, rows, and a unit string.
    """
    try:
        # ── Extract unit string from <p class="sub"> ──────────────────────────
        unit = ""
        sub_p = section.find("p", class_="sub")
        if sub_p:
            # e.g. "Consolidated Figures in Rs. Crores / View Standalone"
            raw_unit = sub_p.get_text(separator=" ", strip=True)
            # Keep only the unit part before the "/" separator
            unit = raw_unit.split("/")[0].strip()
            # Strip "Consolidated " / "Standalone " prefix for brevity
            for prefix in ("Consolidated ", "Standalone "):
                if unit.startswith(prefix):
                    unit = unit[len(prefix):]
                    break

        table = section.find("table")
        if not table:
            return None

        # ── Parse headers ─────────────────────────────────────────────────────
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        else:
            first_tr = table.find("tr")
            headers  = [td.get_text(strip=True) for td in first_tr.find_all(["th", "td"])] if first_tr else []

        # Remove leading empty header (row label column)
        if headers and not headers[0]:
            headers = headers[1:]

        if not headers:
            return None

        # ── Parse body rows ───────────────────────────────────────────────────
        tbody = table.find("tbody") or table
        rows: list[dict[str, str]] = []
        for tr in tbody.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            # Clean label: strip button wrappers, \xa0, trailing "+"
            label = _clean_row_label(cells[0])
            if not label:
                continue
            values = [c.get_text(strip=True) for c in cells[1:]]
            # Pad to match header count
            while len(values) < len(headers):
                values.append("")
            row_dict = {"_label": label}
            for h, v in zip(headers, values):
                row_dict[h] = v
            rows.append(row_dict)

        # Keep only last 12 periods (rightmost = most recent)
        if len(headers) > 12:
            headers = headers[-12:]
            for row in rows:
                vals = [row.get(h, "") for h in headers]
                for h, v in zip(headers, vals):
                    row[h] = v

        return TableSection(headers=headers, rows=rows, unit=unit) if rows else None

    except Exception as exc:
        logger.debug(f"_parse_table_section failed: {exc}")
        return None


def _clean_row_label(cell) -> str:
    """
    Extract clean text from a screener.in row label cell.
    The label may be wrapped in a <button> and contain \xa0 + a blue '+' icon.
    Returns plain ASCII label e.g. 'Sales', 'Net Profit', 'OPM %'.
    """
    import re as _re3
    # Prefer the button text if present (it strips the icon span)
    btn = cell.find("button")
    if btn:
        # Remove any child <span> elements (the blue + icon)
        for span in btn.find_all("span"):
            span.decompose()
        text = btn.get_text(strip=True)
    else:
        text = cell.get_text(strip=True)
    # Replace non-breaking spaces, strip trailing +
    text = text.replace("\xa0", " ").strip().rstrip("+").strip()
    return text


def _extract_opm_from_table(qt: TableSection) -> list[float]:
    """Extract OPM % row from the quarterly results TableSection."""
    for row in qt.rows:
        label = row.get("_label", "").lower()
        if "opm" in label or "operating profit margin" in label:
            vals = [_parse_screener_number(v) for v in row.values() if v and v != row["_label"]]
            numeric = [v for v in vals if v is not None]
            return numeric[-4:]   # last 4 quarters
    return []


def _parse_growth_table_rows(rows, result: FundamentalsResult, kind: str) -> None:
    """
    Parse the data rows of a Compounded Growth sub-table.
    Each row: [label, value]  e.g. ['3 Years:', '13%']
    kind: "sales" | "profit"
    """
    try:
        for tr in rows:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True).lower()
            value = _parse_screener_number(cells[1].get_text(strip=True))
            if "3 year" in label or "3yr" in label or label.startswith("3"):
                if kind == "sales":
                    result.sales_growth_3yr  = value
                else:
                    result.profit_growth_3yr = value
            elif "5 year" in label or "5yr" in label or label.startswith("5"):
                if kind == "sales":
                    result.sales_growth_5yr  = value
                else:
                    result.profit_growth_5yr = value
    except Exception as exc:
        logger.debug(f"_parse_growth_table_rows failed ({kind}): {exc}")


def _extract_shareholding(section, result: FundamentalsResult) -> None:
    """
    Parse the latest Promoter / FII / DII / Public % from the Shareholding section.
    screener.in lists quarters left→right; we take the last (most recent) column.
    """
    try:
        table = section.find("table")
        if not table:
            return
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            label = cells[0].get_text(strip=True).lower()
            nums  = [_parse_screener_number(c.get_text(strip=True)) for c in cells[1:]]
            numeric = [v for v in nums if v is not None]
            if not numeric:
                continue
            latest = numeric[-1]
            if "promoter" in label:
                result.promoter_pct = latest
            elif "fii" in label or "foreign" in label:
                result.fii_pct = latest
            elif "dii" in label or "domestic" in label:
                result.dii_pct = latest
            elif "public" in label:
                result.public_pct = latest
    except Exception as exc:
        logger.debug(f"_extract_shareholding failed: {exc}")


def _fetch_peers_into(warehouse_id: str, result: FundamentalsResult) -> None:
    """
    Call the screener.in internal peer comparison API and populate result.peers,
    result.industry_pe_median, and result.industry_peer_count.

    screener.in returns an HTML fragment (HTMX), not JSON.  The fragment
    contains a <table> with columns:
      S.No. | Name | CMP Rs. | P/E | Mar Cap Rs.Cr. | Div Yld% |
      NP Qtr Rs.Cr. | Qtr Profit Var% | Sales Qtr Rs.Cr. | Qtr Sales Var% | ROCE%

    The last row is a Median row:  ['', 'Median: 33 Co.', '856.95', '82.85', ...]
    which gives us the industry median P/E and the total peer count.
    """
    try:
        from bs4 import BeautifulSoup
        import re as _re2

        url = f"{_SCREENER_BASE}/api/company/{warehouse_id}/peers/"
        headers = {
            **_SCREENER_HEADERS,
            "Referer": _SCREENER_BASE,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "text/html,*/*",
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table")
        if not table:
            logger.debug(f"Peers: no table in response for warehouse_id={warehouse_id}")
            return

        # Map header text → column index (0-based)
        raw_headers = [th.get_text(strip=True) for th in table.find_all("th")]
        hdr = {h.lower(): i for i, h in enumerate(raw_headers)}

        def _col(row_cells, *keys: str) -> float | None:
            for k in keys:
                for hk, idx in hdr.items():
                    if k in hk and idx < len(row_cells):
                        return _safe_float(row_cells[idx].get_text(strip=True).replace(",", ""))
            return None

        peers: list[PeerInfo] = []
        for tr in table.find_all("tr")[1:]:   # skip header row
            cells = tr.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            # Check for the Median row — name cell contains "Median:" with no link
            name_text_raw = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            if name_text_raw.lower().startswith("median"):
                # Extract peer count from "Median: 33 Co."
                m = _re2.search(r"(\d+)", name_text_raw)
                if m:
                    result.industry_peer_count = int(m.group(1))
                # Extract median P/E
                result.industry_pe_median = _col(cells, "p/e")
                continue   # don't add median as a peer row

            # Regular company row — find the <a> link for symbol + company name.
            # screener.in peer table structure:
            #   <td><a href="/company/ircon/">IRCON</a><br>IRCON International Ltd</td>
            # a.get_text() gives the NSE ticker/slug; the full td text includes the
            # company name after the link.  We want the full td text as the display
            # name and the slug (uppercased) as the symbol.
            symbol: str | None = None
            name = ""
            for cell in cells:
                a = cell.find("a")
                if a and "/company/" in (a.get("href") or ""):
                    # Extract symbol from href slug
                    parts = (a["href"] or "").strip("/").split("/")
                    try:
                        idx = parts.index("company")
                        symbol = parts[idx + 1].upper() if idx + 1 < len(parts) else None
                    except ValueError:
                        symbol = None
                    # Full cell text includes company name (may be multi-line after <br>)
                    full_text = cell.get_text(separator=" ", strip=True)
                    # Remove the ticker prefix if it duplicates the slug at the start
                    slug_upper = symbol or ""
                    if full_text.upper().startswith(slug_upper) and len(full_text) > len(slug_upper):
                        name = full_text[len(slug_upper):].strip(" -–:")
                    if not name:
                        name = full_text
                    break

            if not name:
                name = name_text_raw

            peers.append(PeerInfo(
                name=name,
                symbol=symbol,
                price=_col(cells, "cmp", "price"),
                pe_ratio=_col(cells, "p/e"),
                market_cap=_col(cells, "mar cap", "mkt cap", "market cap"),
                div_yield=_col(cells, "div yld", "dividend"),
                net_profit=_col(cells, "np qtr", "net profit"),
                roce=_col(cells, "roce"),
                sales_growth_3yr=_col(cells, "qtr sales var", "sales var"),
                sales_growth_5yr=None,
                roe_3yr=None,
            ))

        result.peers = peers[:12]
        logger.debug(
            f"Peers fetched: {len(result.peers)} peers, "
            f"industry median PE={result.industry_pe_median}, "
            f"peer count={result.industry_peer_count} for warehouse_id={warehouse_id}"
        )

    except Exception as exc:
        logger.debug(f"Peer fetch failed (warehouse_id={warehouse_id}): {exc}")


# ── Utilities ─────────────────────────────────────────────────────────────────

def _parse_screener_number(raw: str) -> float | None:
    """
    Convert screener.in display strings like "2,45,678.90", "12.5%", "1,234 Cr"
    to a plain float.  Returns None if unparseable.
    """
    if not raw:
        return None
    cleaned = raw.replace(",", "").replace("%", "").replace("₹", "").strip()
    # Remove trailing unit labels (Cr, Lakh, B, M, K, etc.)
    cleaned = _re.sub(r"\s*(Cr|cr|Lakh|lakh|B|M|K)\s*$", "", cleaned).strip()
    # Skip compound values like "high / low"
    if "/" in cleaned or "%" in cleaned or len(cleaned) > 20:
        return None
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
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

# ── Industry / Market dashboard ───────────────────────────────────────────────

@dataclass
class IndustryStock:
    """One row from a screener.in /market/... sector/industry table."""
    rank:              int
    name:              str
    symbol:            str | None     # extracted from /company/SYM/ href
    cmp:               float | None   # current market price
    pe_ratio:          float | None
    market_cap:        float | None   # Cr
    div_yield:         float | None
    net_profit_qtr:    float | None   # Cr
    qtr_profit_var:    float | None   # %
    sales_qtr:         float | None   # Cr
    qtr_sales_var:     float | None   # %
    roce:              float | None


@dataclass
class IndustryNode:
    """
    A node in the screener.in market hierarchy.
    Depth 1=L2, 2=L3, 3=L4 (leaf / actual industry).
    stock_count is only set on leaf nodes (L4) — scraped from the L4 page link text.
    children is empty on leaf nodes.
    """
    name:        str
    path:        str               # e.g. /market/IN08/IN0801/
    depth:       int               # 2, 3, or 4
    stock_count: int | None        # set on L4 leaves from /market/ index text
    children:    list["IndustryNode"] = field(default_factory=list)

    @property
    def total_stocks(self) -> int:
        # stock_count is set on L3 nodes from L2 page fetches (authoritative count)
        # and on L4 leaves from L4 page fetches. If set, use it directly.
        if self.stock_count is not None:
            return self.stock_count
        if self.children:
            return sum(c.total_stocks for c in self.children)
        return 0


@dataclass
class SectorInfo:
    """Top-level sector (L1) — name, code, path, full sub-industry tree."""
    code:         str              # e.g. IN08
    name:         str              # e.g. Information Technology
    path:         str              # e.g. /market/IN08/
    children:     list[IndustryNode]   # L2 nodes (each may have L3 → L4 children)

    @property
    def total_stocks(self) -> int:
        return sum(c.total_stocks for c in self.children)

    @property
    def total_stocks_display(self) -> int:
        """L2 stock_counts are authoritative — use them when available."""
        total = 0
        for c in self.children:
            if c.stock_count is not None:
                total += c.stock_count
            else:
                total += c.total_stocks
        return total

    @property
    def flat_industries(self) -> list[IndustryNode]:
        """All leaf (L4) nodes in depth-first order."""
        out: list[IndustryNode] = []
        def _walk(nodes: list[IndustryNode]) -> None:
            for n in nodes:
                if not n.children:
                    out.append(n)
                else:
                    _walk(n.children)
        _walk(self.children)
        return out


@dataclass
class IndustryPageResult:
    """Result for a single sector/industry page."""
    title:   str
    path:    str
    stocks:  list[IndustryStock]
    error:   str | None = None
    fetched_at: float = field(default_factory=time.time)


@dataclass
class IndustryOverviewRow:
    """
    One row from the screener.in /market/ comparison table.
    Covers all 188 L4 industries with aggregate metrics.
    """
    rank:            int
    name:            str
    path:            str            # /market/L1/L2/L3/L4/  — for navigation
    num_companies:   int | None
    total_mktcap:    float | None   # ₹ Cr
    median_mktcap:   float | None   # ₹ Cr
    median_pe:       float | None
    sales_growth:    float | None   # Wtd. Avg Sales Growth %
    avg_opm:         float | None   # Wtd. Avg OPM %
    avg_roce:        float | None   # Wtd. Avg ROCE %
    return_1y:       float | None   # Median 1Y Return %


# 4-hour cache for market/sector pages
_MARKET_CACHE_TTL = 4 * 3600
_sector_index_cache:  list[SectorInfo] | None = None
_industry_overview_cache: list[IndustryOverviewRow] | None = None
_industry_overview_ts:    float = 0.0
_industry_overview_lock   = threading.Lock()
_sector_index_ts:     float = 0.0
_sector_index_lock    = threading.Lock()
_industry_page_cache: dict[str, IndustryPageResult] = {}
_industry_page_lock   = threading.Lock()


# ── Disk persistence for slow scraped caches ──────────────────────────────────
# Avoids re-scraping screener.in on every backend restart.
# Files are written after each successful scrape and read on cache miss.

import json as _json_mod
import pathlib as _pathlib

_DATA_DIR = _pathlib.Path(__file__).resolve().parents[3] / "data"


def _disk_path(name: str) -> _pathlib.Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR / f"_cache_{name}.json"


def _disk_save(name: str, payload: dict) -> None:
    """Persist a JSON payload to disk (non-fatal on failure)."""
    try:
        p = _disk_path(name)
        p.write_text(_json_mod.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.debug(f"disk cache write failed for {name}: {exc}")


def _disk_load(name: str) -> dict | None:
    """Load JSON payload from disk; return None if absent or corrupt."""
    try:
        p = _disk_path(name)
        if not p.exists():
            return None
        return _json_mod.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug(f"disk cache read failed for {name}: {exc}")
        return None


# ── Serialise / deserialise IndustryOverviewRow list ─────────────────────────

def _overview_to_disk(rows: list[IndustryOverviewRow]) -> None:
    import dataclasses as _dc
    _disk_save("industry_overview", {
        "ts": time.time(),
        "rows": [_dc.asdict(r) for r in rows],
    })


def _overview_from_disk() -> tuple[list[IndustryOverviewRow], float] | None:
    d = _disk_load("industry_overview")
    if not d:
        return None
    try:
        rows = [IndustryOverviewRow(**r) for r in d["rows"]]
        return rows, float(d["ts"])
    except Exception:
        return None


# ── Serialise / deserialise SectorInfo list ───────────────────────────────────

def _node_to_dict(n: "IndustryNode") -> dict:
    return {
        "name": n.name, "path": n.path, "depth": n.depth,
        "stock_count": n.stock_count,
        "children": [_node_to_dict(c) for c in n.children],
    }


def _node_from_dict(d: dict) -> "IndustryNode":
    return IndustryNode(
        name=d["name"], path=d["path"], depth=d["depth"],
        stock_count=d.get("stock_count"),
        children=[_node_from_dict(c) for c in d.get("children", [])],
    )


def _sectors_to_disk(sectors: list[SectorInfo]) -> None:
    _disk_save("sector_index", {
        "ts": time.time(),
        "sectors": [
            {
                "code": s.code, "name": s.name, "path": s.path,
                "children": [_node_to_dict(c) for c in s.children],
            }
            for s in sectors
        ],
    })


def _sectors_from_disk() -> tuple[list[SectorInfo], float] | None:
    d = _disk_load("sector_index")
    if not d:
        return None
    try:
        sectors = [
            SectorInfo(
                code=s["code"], name=s["name"], path=s["path"],
                children=[_node_from_dict(c) for c in s.get("children", [])],
            )
            for s in d["sectors"]
        ]
        return sectors, float(d["ts"])
    except Exception:
        return None


def fetch_industry_overview(force: bool = False) -> list[IndustryOverviewRow]:
    """
    Scrape the screener.in /market/ comparison table.

    Returns all 188 L4 industries with aggregate metrics.
    Results cached 4 hours in-process. On cache miss, tries disk first
    before hitting screener.in — avoids re-scraping on every restart.
    Pass force=True to bypass all caches and re-scrape immediately.
    """
    global _industry_overview_cache, _industry_overview_ts

    if not force:
        with _industry_overview_lock:
            if _industry_overview_cache and (time.time() - _industry_overview_ts) < _MARKET_CACHE_TTL:
                return _industry_overview_cache

        # Try disk cache before hitting screener
        disk = _overview_from_disk()
        if disk and (time.time() - disk[1]) < _MARKET_CACHE_TTL:
            rows, ts = disk
            with _industry_overview_lock:
                _industry_overview_cache = rows
                _industry_overview_ts    = ts
            logger.info(f"Industry overview loaded from disk cache ({len(rows)} rows)")
            return rows

    result = _scrape_industry_overview()

    if result:
        with _industry_overview_lock:
            _industry_overview_cache = result
            _industry_overview_ts    = time.time()
        _overview_to_disk(result)

    return result


def _scrape_industry_overview() -> list[IndustryOverviewRow]:
    """Scrape the /market/ comparison table with all 188 industry metrics."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    try:
        resp = requests.get(
            f"{_SCREENER_BASE}/market/",
            headers=_SCREENER_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"screener.in /market/ overview fetch failed: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    tbl  = soup.find("table")
    if not tbl:
        logger.warning("No table found on screener.in /market/")
        return []

    # screener.in /market/ renders all 188 industries in a single flat table,
    # but repeats the header row every 16 rows (S.No. | Industry | …).
    # We skip any row where:
    #   • cell[1] has no href starting with /market/  (header rows link to ?order=asc)
    #   • cell[0] text is not a digit (e.g. "S.No.")
    NCOLS = 10  # S.No | Industry | Companies | Total MCap | Median MCap | P/E | SalesGr | OPM | ROCE | 1YRet

    def _parse_num(text: str) -> float | None:
        raw = text.replace(",", "").replace("%", "").strip()
        if not raw or raw in ("-", "—"):
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    rows: list[IndustryOverviewRow] = []
    for tr in tbl.find_all("tr")[1:]:   # skip the very first header
        cells = tr.find_all(["td", "th"])
        if len(cells) < NCOLS:
            continue

        # Skip repeated header rows — they have no /market/ link in cell[1]
        link = cells[1].find("a", href=True)
        if not link or not link["href"].startswith("/market/"):
            continue

        texts = [cells[i].get_text(strip=True) for i in range(NCOLS)]
        path  = link["href"]

        rank_raw = texts[0].rstrip(".")
        if not rank_raw.isdigit():
            continue   # extra safety — skip any non-numeric rank
        rank = int(rank_raw)

        rows.append(IndustryOverviewRow(
            rank=rank,
            name=texts[1],
            path=path,
            num_companies=int(_parse_num(texts[2])) if _parse_num(texts[2]) is not None else None,
            total_mktcap=_parse_num(texts[3]),
            median_mktcap=_parse_num(texts[4]),
            median_pe=_parse_num(texts[5]),
            sales_growth=_parse_num(texts[6]),
            avg_opm=_parse_num(texts[7]),
            avg_roce=_parse_num(texts[8]),
            return_1y=_parse_num(texts[9]),
        ))

    logger.info(f"Industry overview scraped: {len(rows)} rows")
    return rows


def fetch_sector_index(force: bool = False) -> list[SectorInfo]:
    """
    Scrape the screener.in /market/ index page to build the full sector tree.

    Returns a list of SectorInfo (L1 sectors) each containing their L2
    sub-industry entries (name + path + stock count).
    Cached in-process for 4 hours, persisted to disk to survive restarts.
    Pass force=True to re-scrape immediately.
    """
    global _sector_index_cache, _sector_index_ts

    if not force:
        with _sector_index_lock:
            if _sector_index_cache and (time.time() - _sector_index_ts) < _MARKET_CACHE_TTL:
                return _sector_index_cache

        # Try disk cache before hitting screener
        disk = _sectors_from_disk()
        if disk and (time.time() - disk[1]) < _MARKET_CACHE_TTL:
            sectors, ts = disk
            with _sector_index_lock:
                _sector_index_cache = sectors
                _sector_index_ts    = ts
            logger.info(f"Sector index loaded from disk cache ({len(sectors)} sectors)")
            return sectors

    result = _scrape_sector_index()

    if result:
        with _sector_index_lock:
            _sector_index_cache = result
            _sector_index_ts    = time.time()
        _sectors_to_disk(result)

    return result


def fetch_industry_stocks(path: str, force: bool = False) -> IndustryPageResult:
    """
    Fetch stocks listed on a screener.in market page (L1 or L2).

    `path` is the URL path, e.g. "/market/IN08/" or "/market/IN08/IN0801/".
    All pages are fetched with limit=50 to get more rows per request.
    Cached 4 hours per path.
    """
    key = path.strip("/")

    if not force:
        with _industry_page_lock:
            cached = _industry_page_cache.get(key)
            if cached and (time.time() - cached.fetched_at) < _MARKET_CACHE_TTL:
                return cached

    result = _scrape_industry_page(path)

    with _industry_page_lock:
        _industry_page_cache[key] = result

    return result


# Known L1 sector names (code → display name). Used to label sectors without
# needing extra HTTP requests — screener.in /market/ index only shows L4 links.
_L1_NAMES: dict[str, str] = {
    "IN01": "Commodities",
    "IN02": "Consumer Discretionary",
    "IN03": "Energy",
    "IN04": "Fast Moving Consumer Goods",
    "IN05": "Financial Services",
    "IN06": "Healthcare",
    "IN07": "Industrials",
    "IN08": "Information Technology",
    "IN09": "Services",
    "IN10": "Telecommunication",
    "IN11": "Utilities",
    "IN12": "Diversified",
}

# Fallback L2 names — used when the L1 page fetch doesn't return a name for a
# sub-group code (e.g. rate-limited response or missing <a> text).
_L2_NAMES: dict[str, str] = {
    # IN01 — Commodities
    "IN0101": "Metals & Mining",
    "IN0102": "Chemicals",
    "IN0103": "Agricultural Commodities",
    # IN02 — Consumer Discretionary
    "IN0201": "Automobiles & Auto Components",
    "IN0202": "Consumer Durables",
    "IN0203": "Retailing",
    "IN0204": "Textiles & Apparel",
    "IN0205": "Leisure & Hospitality",
    # IN03 — Energy
    "IN0301": "Oil, Gas & Consumable Fuels",
    "IN0302": "Power Generation",
    # IN04 — Fast Moving Consumer Goods
    "IN0401": "Food & Beverages",
    "IN0402": "Personal & Household Products",
    # IN05 — Financial Services
    "IN0501": "Finance",
    "IN0502": "Capital Markets",
    "IN0503": "Banks",
    "IN0504": "Insurance",
    "IN0505": "Financial Technology (Fintech)",
    # IN06 — Healthcare
    "IN0601": "Pharmaceuticals & Biotechnology",
    "IN0602": "Healthcare Services",
    "IN0603": "Healthcare Equipment & Supplies",
    # IN07 — Industrials
    "IN0701": "Capital Goods",
    "IN0702": "Infrastructure",
    "IN0703": "Transportation",
    "IN0704": "Defence & Aerospace",
    # IN08 — Information Technology
    "IN0801": "Software & IT Services",
    "IN0802": "Technology Hardware",
    # IN09 — Services
    "IN0901": "Commercial & Professional Services",
    "IN0902": "Media & Entertainment",
    "IN0903": "E-Commerce & Internet",
    "IN0904": "Logistics",
    # IN10 — Telecommunication
    "IN1001": "Telecom Services",
    "IN1002": "Telecom Infrastructure",
    # IN11 — Utilities
    "IN1101": "Power Distribution",
    "IN1102": "Water & Waste Management",
    # IN12 — Diversified
    "IN1201": "Conglomerates",
}


def _scrape_sector_index() -> list[SectorInfo]:
    """
    Build the full 4-level sector tree from a single /market/ page load.

    The /market/ index lists all 188 L4 industry links (depth-4 paths).
    We reconstruct the L1→L2→L3→L4 tree purely from those hrefs + link text,
    with no extra HTTP requests per sector.

    L4 link text format: "Specialty Chemicals - 150"  → name + stock_count.
    L2/L3 names are derived from the L4 hrefs of their children — screener
    exposes L2/L3 names only on deeper pages, so we fetch those on-demand
    when the user clicks through (fetch_industry_stocks).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    try:
        resp = requests.get(
            f"{_SCREENER_BASE}/market/",
            headers=_SCREENER_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"screener.in /market/ fetch failed: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # ── Step 1: collect all depth-4 L4 leaf links from /market/ ──────────────
    # The index lists 188 L4 links alphabetically: "Industry Name - NNN" is NOT
    # present here — counts come from individual L2/L3 pages. L4 names ARE here.
    # Structure of href: /market/L1/L2/L3/L4/
    from collections import OrderedDict

    # node_map[l1][l2][l3] = list of {name, path} dicts (L4 leaves)
    node_map: dict[str, dict[str, dict[str, list]]] = OrderedDict()

    for a in soup.find_all("a", href=_re.compile(r"^/market/IN")):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if not text:
            continue
        segs = [s for s in href.split("/") if s and s != "market"]
        if len(segs) != 4:
            continue
        l1, l2, l3, l4 = segs
        node_map.setdefault(l1, OrderedDict()) \
                .setdefault(l2, OrderedDict()) \
                .setdefault(l3, []) \
                .append({"name": text, "path": href})

    # ── Step 2: fetch all L1 sector pages concurrently ────────────────────────
    # Each L1 page provides: sector title + L2 names + L2 stock counts.
    # Each L2 page provides: L3 names + L3 stock counts (fetched on-demand later).
    import concurrent.futures

    def _fetch_l1_names(l1_code: str) -> tuple[str, dict[str, tuple[str, int | None]]]:
        """
        Returns (l1_title, {l2_code: (l2_name, l2_count)}).
        Falls back to empty dict on error.
        """
        path = f"/market/{l1_code}/"
        try:
            r = requests.get(f"{_SCREENER_BASE}{path}", headers=_SCREENER_HEADERS, timeout=20)
            r.raise_for_status()
            s = BeautifulSoup(r.text, "lxml")
            h1 = s.find("h1")
            title = h1.get_text(strip=True).removesuffix(" Companies").strip() if h1 else l1_code
            l2_names: dict[str, tuple[str, int | None]] = {}
            for a in s.find_all("a", href=_re.compile(rf"^/market/{l1_code}/")):
                href = a.get("href", "")
                text = a.get_text(strip=True)
                parts = [seg for seg in href.split("/") if seg and seg != "market"]
                if len(parts) != 2 or not text:
                    continue
                _, l2c = parts
                m2 = _re.search(r"-\s*(\d+)\s*$", text)
                name2  = text[: m2.start()].strip() if m2 else text
                count2 = int(m2.group(1)) if m2 else None
                l2_names[l2c] = (name2, count2)
            return title, l2_names
        except Exception as exc:
            logger.warning(f"Failed to fetch L1 names for {l1_code}: {exc}")
            # Always return a human-readable name — never fall back to the raw code
            return _L1_NAMES.get(l1_code, l1_code), {}

    import time as _t
    import random as _random

    l1_codes = sorted(node_map.keys())
    l1_meta: dict[str, tuple[str, dict]] = {}

    # ── Step 2a: fetch all 12 L1 pages concurrently (max 4 in parallel) ──────
    # Concurrent fetches collapse ~4.8s sequential time to ~1.5s.
    # A semaphore caps concurrency to 4 so we don't hammer screener with 12
    # simultaneous requests. Each worker also sleeps 0.2–0.6s before its request.
    import threading as _th
    sem = _th.Semaphore(4)

    def _fetch_l1_with_delay(code: str) -> tuple[str, tuple[str, dict]]:
        _t.sleep(_random.uniform(0.2, 0.6))
        with sem:
            try:
                return code, _fetch_l1_names(code)
            except Exception:
                return code, (_L1_NAMES.get(code, code), {})

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for code, meta in pool.map(_fetch_l1_with_delay, l1_codes):
            l1_meta[code] = meta

    # ── Step 3: fetch L2 pages to get L3 names + counts (best-effort) ────────
    # We fetch L2 pages that have multiple L3 sub-groups needing labels.
    # Uses a requests.Session to share a TCP connection and avoid reconnect overhead.
    # Each L2 page fetch is paced at 1.2s to respect screener.in rate limits.
    all_l2_paths: list[tuple[str, str, str]] = []
    for l1_code, l2_map in node_map.items():
        for l2_code, l3_map in l2_map.items():
            if any(len(l4s) > 1 for l4s in l3_map.values()):
                all_l2_paths.append((l1_code, l2_code, f"/market/{l1_code}/{l2_code}/"))

    l2_meta: dict[tuple[str, str], dict] = {}
    with requests.Session() as sess:
        sess.headers.update(_SCREENER_HEADERS)
        for l1c, l2c, p in all_l2_paths:
            _t.sleep(1.2)   # conservative pace — L2 pages 429 at <1.0s
            try:
                r = sess.get(f"{_SCREENER_BASE}{p}", timeout=20)
                r.raise_for_status()
                s2 = BeautifulSoup(r.text, "lxml")
                l3n: dict[str, tuple[str, int | None]] = {}
                for a in s2.find_all("a", href=_re.compile(rf"^/market/{l1c}/{l2c}/")):
                    href = a.get("href", "")
                    text = a.get_text(strip=True)
                    parts = [x for x in href.split("/") if x and x != "market"]
                    if len(parts) != 3 or not text:
                        continue
                    _, _, l3c = parts
                    m3 = _re.search(r"-\s*(\d+)\s*$", text)
                    name3  = text[: m3.start()].strip() if m3 else text
                    count3 = int(m3.group(1)) if m3 else None
                    l3n[l3c] = (name3, count3)
                l2_meta[(l1c, l2c)] = l3n
            except Exception as exc:
                logger.debug(f"L2 page fetch failed for {p}: {exc}")

    # ── Step 4: assemble the full tree with resolved names + counts ───────────
    sectors: list[SectorInfo] = []

    for l1_code in l1_codes:
        l2_map = node_map[l1_code]
        l1_title, l1_l2_names = l1_meta.get(l1_code, (_L1_NAMES.get(l1_code, l1_code), {}))
        l2_nodes: list[IndustryNode] = []

        for l2_code, l3_map in l2_map.items():
            l2_name, l2_count = l1_l2_names.get(l2_code, ("", None))
            l3_names_map = l2_meta.get((l1_code, l2_code), {})
            l3_nodes: list[IndustryNode] = []
            for l3_code, l4_list in l3_map.items():
                l3_name, l3_count = l3_names_map.get(l3_code, ("", None))

                l4_nodes = [
                    IndustryNode(
                        name=item["name"],
                        path=item["path"],
                        depth=4,
                        stock_count=None,   # not in index; set when L4 page is fetched
                    )
                    for item in l4_list
                ]

                if len(l4_nodes) == 1:
                    # Single L4 under L3: collapse — show the L4 directly
                    leaf = l4_nodes[0]
                    # Override name with L3 name if L4 name is the same (duplicates)
                    l3_nodes.append(leaf)
                else:
                    l3_nodes.append(IndustryNode(
                        name=l3_name or f"{l2_name} sub-group",
                        path=f"/market/{l1_code}/{l2_code}/{l3_code}/",
                        depth=3,
                        stock_count=l3_count,
                        children=l4_nodes,
                    ))

            if len(l3_nodes) == 1 and not l3_nodes[0].children:
                # Single leaf under L2: promote directly
                l2_nodes.append(l3_nodes[0])
            else:
                l2_nodes.append(IndustryNode(
                    name=l2_name or _L2_NAMES.get(l2_code, l2_code),
                    path=f"/market/{l1_code}/{l2_code}/",
                    depth=2,
                    stock_count=l2_count,
                    children=l3_nodes,
                ))

        sectors.append(SectorInfo(
            code=l1_code,
            name=l1_title or _L1_NAMES.get(l1_code, l1_code),
            path=f"/market/{l1_code}/",
            children=l2_nodes,
        ))

    logger.info(
        f"Sector index: {len(sectors)} sectors, "
        f"{sum(len(s.flat_industries) for s in sectors)} L4 industries, "
        f"{len(all_l2_paths)} L2 pages fetched"
    )
    return sectors


def _scrape_industry_page(path: str) -> IndustryPageResult:
    """Scrape a single sector or industry stock table from screener.in."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return IndustryPageResult(title="", path=path, stocks=[], error="beautifulsoup4 not installed")

    url = f"{_SCREENER_BASE}{path}?limit=50"
    try:
        resp = requests.get(url, headers=_SCREENER_HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        return IndustryPageResult(title="", path=path, stocks=[], error=str(exc))

    soup = BeautifulSoup(resp.text, "lxml")

    h1 = soup.find("h1")
    title = h1.get_text(strip=True).removesuffix(" Companies").strip() if h1 else path

    tbl = soup.find("table")
    if not tbl:
        return IndustryPageResult(title=title, path=path, stocks=[], error="No table found on page")

    # The table has duplicate header columns (screener renders two halves side-by-side).
    # Take the first occurrence of each header column name.
    header_cells = tbl.find_all("th")
    # Find the midpoint where headers repeat
    all_headers = [h.get_text(strip=True) for h in header_cells]
    # Deduplicate: take first N unique headers
    seen_h: list[str] = []
    for h in all_headers:
        if h not in seen_h:
            seen_h.append(h)
        else:
            break   # stop at first repeat → that's the column count
    ncols = len(seen_h)  # number of real columns

    stocks: list[IndustryStock] = []
    for tr in tbl.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) < ncols:
            continue
        # Only take first ncols cells
        cells = cells[:ncols]
        texts = [c.get_text(strip=True) for c in cells]

        # Extract symbol from company link href: /company/SYM/...
        sym: str | None = None
        link = tr.find("a", href=_re.compile(r"^/company/"))
        if link:
            parts = link["href"].strip("/").split("/")
            if len(parts) >= 2:
                sym = parts[1].upper()

        def _col(idx: int) -> float | None:
            if idx >= len(texts):
                return None
            return _parse_screener_number(texts[idx])

        # Column order: S.No | Name | CMP | P/E | Mar Cap | Div Yld | NP Qtr | Qtr Profit Var | Sales Qtr | Qtr Sales Var | ROCE
        try:
            rank = int(texts[0].rstrip(".")) if texts[0].rstrip(".").isdigit() else len(stocks) + 1
        except Exception:
            rank = len(stocks) + 1

        stocks.append(IndustryStock(
            rank=rank,
            name=texts[1] if len(texts) > 1 else "",
            symbol=sym,
            cmp=_col(2),
            pe_ratio=_col(3),
            market_cap=_col(4),
            div_yield=_col(5),
            net_profit_qtr=_col(6),
            qtr_profit_var=_col(7),
            sales_qtr=_col(8),
            qtr_sales_var=_col(9),
            roce=_col(10),
        ))

    logger.info(f"Industry page '{title}' ({path}): {len(stocks)} stocks")
    return IndustryPageResult(title=title, path=path, stocks=stocks)



# ── Screener.in authenticated session + penny-stock screen ───────────────────

import threading as _ss_threading

@dataclass
class PennyStock:
    """One row from the penny-stock screener screen."""
    rank:            int
    name:            str
    symbol:          str | None
    cmp:             float | None   # current market price ₹
    market_cap:      float | None   # ₹ Cr
    pe_ratio:        float | None
    roce:            float | None   # %
    div_yield:       float | None   # %
    net_profit_qtr:  float | None   # ₹ Cr
    qtr_sales_var:   float | None   # % QoQ
    high_52w:        float | None   # ₹
    low_52w:         float | None   # ₹
    pct_from_52w_high: float | None # % below 52-week high (negative = below)


_screener_session:     "requests.Session | None" = None
_screener_session_lock = _ss_threading.Lock()
_screener_session_user: str = ""   # email used for current session

# 1-hour cache for penny-stock results
_penny_cache:    "list[PennyStock] | None" = None
_penny_cache_ts: float = 0.0
_penny_cache_lock = _ss_threading.Lock()
_PENNY_CACHE_TTL  = 3600   # 1 hour


def _get_screener_session(email: str, password: str) -> "requests.Session | None":
    """
    Return an authenticated requests.Session for screener.in.
    Re-uses the existing session if the credentials match; re-logins on
    credential change or after 403/session-expiry (caller's responsibility
    to call this again with force=True).
    Thread-safe.
    """
    global _screener_session, _screener_session_user

    with _screener_session_lock:
        if _screener_session is not None and _screener_session_user == email:
            return _screener_session

        sess = requests.Session()
        sess.headers.update(_SCREENER_HEADERS)

        # Step 1: GET login page to harvest CSRF token
        try:
            resp = sess.get(f"{_SCREENER_BASE}/login/", timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"screener.in login page fetch failed: {exc}")
            return None

        # CSRF token is in a hidden input or a cookie named csrftoken
        from bs4 import BeautifulSoup as _BSL
        soup = _BSL(resp.text, "lxml")
        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        csrf = csrf_input["value"] if csrf_input else sess.cookies.get("csrftoken", "")

        # Step 2: POST credentials
        try:
            login_resp = sess.post(
                f"{_SCREENER_BASE}/login/",
                data={
                    "username":            email,
                    "password":            password,
                    "csrfmiddlewaretoken": csrf,
                    "next":                "/",
                },
                headers={"Referer": f"{_SCREENER_BASE}/login/"},
                timeout=15,
                allow_redirects=True,
            )
            login_resp.raise_for_status()
        except Exception as exc:
            logger.error(f"screener.in login POST failed: {exc}")
            return None

        # Verify login: authenticated pages set a "sessionid" cookie
        if "sessionid" not in sess.cookies:
            logger.error("screener.in login failed — no sessionid cookie (wrong credentials?)")
            return None

        _screener_session      = sess
        _screener_session_user = email
        logger.info("screener.in login successful")
        return sess


def fetch_penny_stocks(
    max_price: float = 50.0,
    min_volume_cr: float = 1.0,
    min_market_cap_cr: float = 10.0,
    max_market_cap_cr: float = 500.0,
    force: bool = False,
) -> "list[PennyStock] | None":
    """
    Fetch penny stocks from screener.in using the authenticated /screen/raw/ API.

    Requires SCREENER_EMAIL and SCREENER_PASSWORD in settings.
    Returns None when credentials are not configured or login fails.
    Returns [] when the screen runs but finds no results.
    Results are cached 1 hour in-process.

    Screen criteria (all configurable via params):
      Current Price < max_price
      Market Capitalization > min_market_cap_cr
      Market Capitalization < max_market_cap_cr
    """
    global _penny_cache, _penny_cache_ts
    from backend.app.core.config import get_settings
    cfg = get_settings()

    email    = getattr(cfg, "screener_email",    "")
    password = getattr(cfg, "screener_password", "")
    if not email or not password:
        logger.warning("SCREENER_EMAIL / SCREENER_PASSWORD not set — penny stocks unavailable")
        return None

    # Serve from cache
    if not force:
        with _penny_cache_lock:
            if _penny_cache is not None and (time.time() - _penny_cache_ts) < _PENNY_CACHE_TTL:
                return list(_penny_cache)

    sess = _get_screener_session(email, password)
    if sess is None:
        return None

    try:
        from bs4 import BeautifulSoup as _BSP
    except ImportError:
        logger.warning("beautifulsoup4 not installed")
        return None

    # screener.in screen query syntax: field op value AND ...
    query = (
        f"Current Price < {max_price} AND "
        f"Market Capitalization > {min_market_cap_cr} AND "
        f"Market Capitalization < {max_market_cap_cr}"
    )

    try:
        # GET /screen/raw/?query=...  — returns a full HTML page with one <table>
        # Session expired → screener redirects to /login/
        resp = sess.get(
            f"{_SCREENER_BASE}/screen/raw/",
            params={"query": query, "limit": "200"},
            headers={"Referer": f"{_SCREENER_BASE}/screen/new/"},
            timeout=30,
        )
        resp.raise_for_status()

        if "/login/" in resp.url:
            logger.warning("screener.in session expired — re-logging in")
            with _screener_session_lock:
                global _screener_session
                _screener_session = None
            sess = _get_screener_session(email, password)
            if sess is None:
                return None
            resp = sess.get(
                f"{_SCREENER_BASE}/screen/raw/",
                params={"query": query, "limit": "200"},
                headers={"Referer": f"{_SCREENER_BASE}/screen/new/"},
                timeout=30,
            )
            resp.raise_for_status()

    except Exception as exc:
        logger.error(f"screener.in penny screen fetch failed: {exc}")
        return None

    # Parse the returned HTML table.
    # The page has a single <table>; the first <tr> in tbody contains sort-link
    # <th> elements (not data), so skip any <tr> whose cells are all empty.
    soup = _BSP(resp.text, "lxml")
    tbl  = soup.find("table")
    if not tbl:
        logger.warning("penny screen: no table in screener.in response")
        return []

    # Detect column order from the *first* <tr> that has <th> elements.
    # /screen/raw/ uses <thead>/<tbody> — fall back to scanning all <tr>s.
    thead = tbl.find("thead")
    if thead:
        raw_headers = [th.get_text(strip=True).lower() for th in thead.find_all("th")]
    else:
        raw_headers = [th.get_text(strip=True).lower() for th in tbl.find_all("th")]
    # Deduplicate while preserving first occurrence
    seen: set[str] = set()
    headers: list[str] = []
    for h in raw_headers:
        if h not in seen:
            seen.add(h)
            headers.append(h)

    def _hi(keyword: str) -> int | None:
        for i, h in enumerate(headers):
            if keyword in h:
                return i
        return None

    # Column indices — screener /screen/raw/ default columns:
    # S.No. | Company | CMPRs. | P/E | Mar Cap Rs.Cr. | Div Yld% |
    # NP Qtr Rs.Cr. | Qtr Profit Var% | Sales Qtr Rs.Cr. | Qtr Sales Var% |
    # ROCE% | Ind PE | Sales Var 3Yrs% | ROE 3Yr% | ROE 5Yr% | Sales Var 5Yrs%
    idx_no    = 0
    idx_name  = _hi("company") or _hi("name") or 1
    idx_cmp   = _hi("cmp") or _hi("price") or 2
    idx_mc    = _hi("cap") or 4
    idx_pe    = _hi("p/e") or 3
    idx_dy    = _hi("div") or 5
    idx_np    = _hi("np qtr") or _hi("net profit") or 6
    idx_sv    = _hi("qtr sales var") or _hi("sales var") or 9
    idx_roce  = _hi("roce") or 10
    idx_52h: int | None = _hi("52w high") or _hi("52 week high")
    idx_52l: int | None = _hi("52w low")  or _hi("52 week low")

    # tbody rows — skip header-repeat rows (cells all empty or no <td>)
    tbody = tbl.find("tbody")
    all_trs = tbody.find_all("tr") if tbody else tbl.find_all("tr")[1:]

    results: list[PennyStock] = []
    rank = 0
    for tr in all_trs:
        cells = tr.find_all("td")
        if not cells:
            continue
        # Skip sort-link header rows (first cell is a sort anchor, not a number)
        first_text = cells[0].get_text(strip=True)
        if not first_text or not first_text.rstrip(".").isdigit():
            continue

        rank += 1

        def _get(idx: int | None) -> float | None:
            if idx is None or idx >= len(cells):
                return None
            return _parse_screener_number(cells[idx].get_text(strip=True))

        # Extract symbol from /company/<SLUG>/  or  /company/<SLUG>/consolidated/
        # SLUG may be an ISIN (numeric, e.g. "523222") or a ticker string ("NOIDATOLL")
        sym: str | None = None
        link = tr.find("a", href=_re.compile(r"^/company/"))
        if link:
            parts = [p for p in link["href"].strip("/").split("/") if p]
            # parts = ["company", slug, ...]  → slug is parts[1]
            if len(parts) >= 2:
                slug = parts[1].upper()
                # If it looks like a pure ISIN number, skip — use company name as fallback
                sym = slug if not slug.isdigit() else None

        cmp = _get(idx_cmp)
        h52 = _get(idx_52h)
        pct_from_high = round((cmp - h52) / h52 * 100, 1) if cmp and h52 and h52 > 0 else None

        name_text = cells[idx_name].get_text(strip=True) if idx_name is not None and idx_name < len(cells) else ""

        results.append(PennyStock(
            rank=rank,
            name=name_text,
            symbol=sym,
            cmp=cmp,
            market_cap=_get(idx_mc),
            pe_ratio=_get(idx_pe),
            roce=_get(idx_roce),
            div_yield=_get(idx_dy),
            net_profit_qtr=_get(idx_np),
            qtr_sales_var=_get(idx_sv),
            high_52w=h52,
            low_52w=_get(idx_52l),
            pct_from_52w_high=pct_from_high,
        ))

    logger.info(f"penny screen: {len(results)} stocks (price < ₹{max_price})")

    with _penny_cache_lock:
        _penny_cache    = results
        _penny_cache_ts = time.time()

    return results
