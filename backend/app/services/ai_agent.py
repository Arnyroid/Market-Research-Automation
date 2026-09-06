"""
AI Agent service.

Principle: the LLM interprets, it does not compute.
All indicators and signals are computed deterministically in Python and passed
as structured input. The LLM returns structured JSON stored in agent_analysis.

Public API
----------
  run_analysis(symbol, exchange, db)  →  AgentAnalysis (ORM row, not yet committed)
  run_sector_analysis(overview_rows)  →  dict (structured JSON, cached 24h in-process)
"""
from __future__ import annotations

import time
import threading
from datetime import date, timedelta
from typing import Optional

from google import genai
from google.genai import types as genai_types
from loguru import logger
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import AgentAnalysis, AgentFeedback, RiskProfile
from backend.app.services.data_fetch import fetch_fundamentals, fetch_news, IndustryOverviewRow
from backend.app.services.indicators import IndicatorSnapshot, compute_indicators

settings = get_settings()

# ── In-flight lock — prevents duplicate concurrent Gemini calls ───────────────
# Maps "SYMBOL:EXCHANGE" → True while a call is running.
_analysis_running: set[str] = set()
_analysis_running_lock = threading.Lock()

# ── Prompt templates ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an experienced Indian equity market analyst assistant.
You provide clear, evidence-based analysis grounded in technical indicators,
deterministic signals, and recent news context.

Rules:
- Base your recommendation ONLY on the data provided — never hallucinate prices or events.
- Give a concrete recommendation: BUY, HOLD, SELL, or AVOID.
  - BUY   = indicators and signals are broadly bullish; risk is acceptable for the user's profile.
  - HOLD  = mixed signals or existing position worth keeping; no clear entry/exit trigger.
  - SELL  = bearish signals dominant; consider reducing or exiting positions.
  - AVOID = high risk, overbought, or insufficient data for a confident view.
- Always include a rationale explaining exactly which signals drove the recommendation.
- Always frame analysis as educational — include caveats and a disclaimer.
- You respond ONLY with valid JSON matching the schema — no markdown fences, no extra text.
"""

_USER_TEMPLATE = """\
Analyse the following Indian equity and return a JSON object.

## Stock
Symbol: {symbol}  |  Exchange: {exchange}

## Current Price & Recent Returns
Current price:          ₹{current_price}
1-day change:           {pct_change_1d}%
5-day change:           {pct_change_5d}%
30-day change:          {pct_change_30d}%

## Technical Indicators (computed in Python — do not recalculate)
RSI (14):               {rsi_14}
SMA-20:                 ₹{sma_20}
SMA-50:                 ₹{sma_50}
EMA-20:                 ₹{ema_20}
Price vs SMA-20:        {price_vs_sma20_pct}%
Realized vol (30d ann): {realized_volatility_30d}%

## Deterministic Signal Audit (pre-computed rules — interpret, do not recompute)
{signal_context}

## Fundamental Data (scraped from screener.in — do not recalculate)
{fundamentals_context}

## Recent News Headlines (from Yahoo Finance — use as supporting context only)
{news_context}

## User Risk Profile
Time horizon:           {time_horizon}
Loss tolerance:         {loss_tolerance}
Experience level:       {experience_level}

## Past Signal Track Record (last 3 analyses on this symbol)
{feedback_digest}

## Response schema (return ONLY this JSON, no markdown, no extra text)
{{
  "summary": "<2-3 sentence plain-language trend summary incorporating indicators, fundamentals and news>",
  "recommendation": "<BUY|HOLD|SELL|AVOID>",
  "rationale": "<2-3 sentences explaining exactly which signals, fundamental metrics and news drove the recommendation>",
  "risk_flag": "<low|medium|high>",
  "caveats": "<1-2 sentences on key uncertainties or data limitations>",
  "disclaimer": "This is educational analysis only, not financial advice. Please consult a SEBI-registered advisor before making investment decisions."
}}
"""

# ── Main function ─────────────────────────────────────────────────────────────

def run_analysis(symbol: str, exchange: str, db: Session) -> Optional[AgentAnalysis]:
    """
    Compute indicators + signals, fetch news, call Gemini, store result.
    Returns the unsaved AgentAnalysis ORM row (caller must db.add + db.commit).
    Returns None if the API key is not configured or all models fail.
    """
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — skipping AI analysis")
        return None

    # In-flight deduplication — skip if the same symbol is already being analysed
    run_key = f"{symbol.upper()}:{exchange.upper()}"
    with _analysis_running_lock:
        if run_key in _analysis_running:
            logger.info(f"run_analysis: {run_key} already in flight, skipping duplicate")
            return None
        _analysis_running.add(run_key)

    try:
        return _run_analysis_inner(symbol, exchange, db)
    finally:
        with _analysis_running_lock:
            _analysis_running.discard(run_key)


def _run_analysis_inner(symbol: str, exchange: str, db: Session) -> Optional[AgentAnalysis]:
    """Inner implementation — called only when no duplicate is in flight."""

    # ── 1. Compute indicators + signals ──────────────────────────────────────
    snap: IndicatorSnapshot = compute_indicators(symbol, exchange, db)

    # ── 1b. Fetch fundamentals (cached 24h, non-blocking on failure) ──────────
    fund = None
    try:
        fund = fetch_fundamentals(symbol, exchange)
    except Exception as exc:
        logger.debug(f"fetch_fundamentals skipped for {symbol}: {exc}")

    # ── 2. Fetch news headlines ───────────────────────────────────────────────
    news_items = fetch_news(symbol, exchange, max_items=5)
    if news_items:
        news_lines = "\n".join(
            f"- [{n.published_at}] {n.title} ({n.publisher})"
            + (f"\n  Summary: {n.summary}" if n.summary else "")
            for n in news_items
        )
    else:
        news_lines = "No recent news headlines available."

    # ── 3. Load risk profile ──────────────────────────────────────────────────
    risk = db.query(RiskProfile).first()
    risk_ctx = {
        "time_horizon":     risk.time_horizon     if risk else "medium",
        "loss_tolerance":   risk.loss_tolerance   if risk else "medium",
        "experience_level": risk.experience_level if risk else "intermediate",
    }

    # ── 4. Build feedback digest ──────────────────────────────────────────────
    feedback_digest = _build_feedback_digest(symbol, exchange, db)

    # ── 5. Build prompt ───────────────────────────────────────────────────────
    user_msg = _USER_TEMPLATE.format(
        symbol=symbol,
        exchange=exchange,
        current_price=_fmt(snap.current_price),
        pct_change_1d=_fmt(snap.pct_change_1d),
        pct_change_5d=_fmt(snap.pct_change_5d),
        pct_change_30d=_fmt(snap.pct_change_30d),
        rsi_14=_fmt(snap.rsi_14),
        sma_20=_fmt(snap.sma_20),
        sma_50=_fmt(snap.sma_50),
        ema_20=_fmt(snap.ema_20),
        price_vs_sma20_pct=_fmt(snap.price_vs_sma20_pct),
        realized_volatility_30d=_fmt(snap.realized_volatility_30d),
        signal_context=snap.signal_context or "Insufficient data for signal generation.",
        fundamentals_context=_build_fundamentals_context(fund),
        news_context=news_lines,
        feedback_digest=feedback_digest,
        **risk_ctx,
    )

    # ── 6. Call Gemini with enforced JSON schema ──────────────────────────────
    # response_mime_type + response_schema guarantees a parse-safe JSON response
    # and eliminates all regex fence-stripping code.
    _analysis_schema = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "summary":        genai_types.Schema(type=genai_types.Type.STRING),
            "recommendation": genai_types.Schema(type=genai_types.Type.STRING, enum=["BUY", "HOLD", "SELL", "AVOID"]),
            "rationale":      genai_types.Schema(type=genai_types.Type.STRING),
            "risk_flag":      genai_types.Schema(type=genai_types.Type.STRING, enum=["low", "medium", "high"]),
            "caveats":        genai_types.Schema(type=genai_types.Type.STRING),
            "disclaimer":     genai_types.Schema(type=genai_types.Type.STRING),
        },
        required=["summary", "recommendation", "rationale", "risk_flag", "caveats", "disclaimer"],
    )

    client = genai.Client(api_key=settings.gemini_api_key)
    gen_cfg = genai_types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        max_output_tokens=1024,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=_analysis_schema,
    )

    models_to_try = [settings.gemini_model]
    if settings.gemini_model_fallback and settings.gemini_model_fallback != settings.gemini_model:
        models_to_try.append(settings.gemini_model_fallback)

    structured: dict | None = None
    for attempt_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=attempt_model,
                contents=user_msg,
                config=gen_cfg,
            )
            raw_text = (response.text or "").strip()
            if raw_text:
                import json as _json
                structured = _json.loads(raw_text)
                logger.info(f"Gemini OK using {attempt_model} for {symbol}")
                break
            logger.warning(f"Gemini returned empty response from {attempt_model}, trying fallback")
        except Exception as exc:
            err_str = str(exc)
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                logger.warning(f"Gemini {attempt_model} overloaded for {symbol}, trying fallback")
            else:
                logger.error(f"Gemini API call failed for {symbol} ({attempt_model}): {exc}")
                return None   # non-recoverable (bad key, 404, etc.)

    if not structured:
        logger.error(f"All Gemini models unavailable for {symbol}")
        return None

    # ── 7. Validate / normalise fields ───────────────────────────────────────
    # Schema enforcement means enums are already valid, but normalise defensively
    risk_flag = structured.get("risk_flag", "medium")
    if risk_flag not in ("low", "medium", "high"):
        risk_flag = "medium"

    recommendation = structured.get("recommendation", "HOLD").upper()
    if recommendation not in ("BUY", "HOLD", "SELL", "AVOID"):
        recommendation = "HOLD"
    structured["recommendation"] = recommendation

    # ── 8. Build ORM row ──────────────────────────────────────────────────────
    import dataclasses as _dc
    fund_dict: dict | None = None
    if fund and not fund.error:
        # Store a compact snapshot (exclude heavy table sections for DB storage)
        fund_dict = {
            "pe_ratio":         fund.pe_ratio,
            "book_value":       fund.book_value,
            "roce":             fund.roce,
            "roe":              fund.roe,
            "div_yield":        fund.div_yield,
            "market_cap":       fund.market_cap,
            "debt_to_equity":   fund.debt_to_equity,
            "eps":              fund.eps,
            "promoter_pct":     fund.promoter_pct,
            "fii_pct":          fund.fii_pct,
            "dii_pct":          fund.dii_pct,
            "public_pct":       fund.public_pct,
            "opm_trend":        fund.opm_trend,
            "sales_growth_3yr": fund.sales_growth_3yr,
            "sales_growth_5yr": fund.sales_growth_5yr,
            "profit_growth_3yr":fund.profit_growth_3yr,
            "profit_growth_5yr":fund.profit_growth_5yr,
            "sector":           fund.sector,
            "industry":         fund.industry,
            "pros":             fund.pros,
            "cons":             fund.cons,
        }

    review_date = (date.today() + timedelta(days=settings.agent_feedback_days)).isoformat()
    analysis = AgentAnalysis(
        symbol=symbol,
        exchange=exchange,
        indicators_snapshot=snap.to_dict(),
        fundamentals_snapshot=fund_dict,
        llm_output=raw_text,
        risk_flag=risk_flag,
        structured_output=structured,
        target_review_date=review_date,
    )
    return analysis


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_feedback_digest(symbol: str, exchange: str, db: Session) -> str:
    past = (
        db.query(AgentAnalysis)
        .filter(
            AgentAnalysis.symbol == symbol,
            AgentAnalysis.exchange == exchange,
        )
        .order_by(AgentAnalysis.generated_at.desc())
        .limit(3)
        .all()
    )

    if not past:
        return "No prior analyses available for this symbol."

    lines = []
    for a in past:
        rec = ""
        if a.structured_output:
            rec = a.structured_output.get("recommendation", "")
            rec = f", recommendation={rec}" if rec else ""
        feedback_rows = a.feedback
        if feedback_rows:
            fb = feedback_rows[-1]
            usefulness = (
                "flag was useful" if fb.was_flag_useful
                else "flag was not useful" if fb.was_flag_useful is False
                else "outcome pending"
            )
            lines.append(
                f"- {a.generated_at.date()}: risk_flag={a.risk_flag}{rec}, "
                f"outcome={_fmt(fb.outcome_pct_change)}% change, {usefulness}"
            )
        else:
            lines.append(
                f"- {a.generated_at.date()}: risk_flag={a.risk_flag}{rec}, no feedback yet"
            )

    return "\n".join(lines)


def _build_fundamentals_context(fund) -> str:
    """
    Build a structured text block of fundamental metrics for the Gemini prompt.
    Returns a placeholder string if fundamentals are unavailable.
    """
    if fund is None or fund.error:
        return "Fundamental data not available (screener.in scraping failed or not configured)."

    lines: list[str] = []

    # Core ratios
    if fund.pe_ratio is not None:
        lines.append(f"P/E Ratio:              {fund.pe_ratio:.1f}x")
    if fund.book_value is not None:
        lines.append(f"Book Value per Share:   ₹{fund.book_value:.2f}")
    if fund.roce is not None:
        lines.append(f"ROCE:                   {fund.roce:.1f}%")
    if fund.roe is not None:
        lines.append(f"ROE:                    {fund.roe:.1f}%")
    if fund.div_yield is not None:
        lines.append(f"Dividend Yield:         {fund.div_yield:.2f}%")
    if fund.market_cap is not None:
        lines.append(f"Market Cap:             ₹{fund.market_cap:,.0f} Cr")
    if fund.debt_to_equity is not None:
        lines.append(f"Debt / Equity:          {fund.debt_to_equity:.2f}x")
    if fund.eps is not None:
        lines.append(f"EPS (TTM):              ₹{fund.eps:.2f}")

    # Growth rates
    if fund.sales_growth_3yr is not None:
        lines.append(f"Sales CAGR (3yr):       {fund.sales_growth_3yr:.1f}%")
    if fund.sales_growth_5yr is not None:
        lines.append(f"Sales CAGR (5yr):       {fund.sales_growth_5yr:.1f}%")
    if fund.profit_growth_3yr is not None:
        lines.append(f"Profit CAGR (3yr):      {fund.profit_growth_3yr:.1f}%")
    if fund.profit_growth_5yr is not None:
        lines.append(f"Profit CAGR (5yr):      {fund.profit_growth_5yr:.1f}%")

    # Shareholding
    sh_parts: list[str] = []
    if fund.promoter_pct is not None:
        sh_parts.append(f"Promoter {fund.promoter_pct:.1f}%")
    if fund.fii_pct is not None:
        sh_parts.append(f"FII {fund.fii_pct:.1f}%")
    if fund.dii_pct is not None:
        sh_parts.append(f"DII {fund.dii_pct:.1f}%")
    if fund.public_pct is not None:
        sh_parts.append(f"Public {fund.public_pct:.1f}%")
    if sh_parts:
        lines.append(f"Shareholding (latest):  {', '.join(sh_parts)}")

    # OPM trend
    if fund.opm_trend:
        trend_str = " → ".join(f"{v:.1f}%" for v in fund.opm_trend)
        lines.append(f"OPM Trend (4 qtrs):     {trend_str}")

    # Pros / Cons
    if fund.pros:
        lines.append("Pros (per screener.in): " + "; ".join(fund.pros[:3]))
    if fund.cons:
        lines.append("Cons (per screener.in): " + "; ".join(fund.cons[:3]))

    # Sector / industry
    if fund.sector or fund.industry:
        lines.append(f"Sector/Industry:        {fund.sector or ''} / {fund.industry or ''}".strip(" /"))

    return "\n".join(lines) if lines else "No fundamental data parsed from screener.in."


def _fmt(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


# ── Sector-level analysis ─────────────────────────────────────────────────────

_SECTOR_SYSTEM_PROMPT = """\
You are a senior Indian equity market strategist providing daily sector rotation guidance.
You receive aggregate metrics for all 188 NSE/BSE industries from screener.in.

Rules:
- Base ALL conclusions strictly on the data provided — median P/E, ROCE, OPM, sales growth, 1Y return.
- Never hallucinate values, prices or news events.
- Sector signals: BUY = attractive valuation + strong fundamentals + positive momentum.
  HOLD = mixed or neutral signals. AVOID = expensive, deteriorating margins, or negative returns.
- Be specific — cite the exact metrics that drove each call.
- Respond ONLY with valid JSON matching the schema — no markdown fences, no extra text.
"""

_SECTOR_USER_TEMPLATE = """\
Today's date: {today}

Below are aggregate metrics for all 188 Indian equity industries sourced from screener.in.
Metrics: Cos. = number of listed companies, Total MCap (₹ Cr), Median P/E, Sales Growth % (wtd avg),
OPM % (operating profit margin, wtd avg), ROCE % (wtd avg), 1Y Return % (median).

{industry_table}

Based on these metrics, provide:
1. A 3-4 sentence broad market summary (overall valuations, dominant trends, rotation themes).
2. For each L1 sector (Commodities, Consumer Discretionary, Energy, FMCG, Financial Services,
   Healthcare, Industrials, Information Technology, Services, Telecommunication, Utilities, Diversified):
   signal (BUY / HOLD / AVOID), 1-sentence rationale, and the 2-3 key metrics that drove it.
3. Top-5 BUY industries (L4 names) with rationale.
4. Top-5 AVOID industries (L4 names) with rationale.

## Response schema (return ONLY this JSON, no markdown, no extra text)
{{
  "market_summary": "<3-4 sentence overall market view>",
  "generated_at": "{today}",
  "sectors": [
    {{
      "name": "<L1 sector name>",
      "signal": "<BUY|HOLD|AVOID>",
      "rationale": "<1 sentence>",
      "key_metrics": "<e.g. ROCE 22%, P/E 18x, 1Y +12%>"
    }}
  ],
  "top_buy_industries": [
    {{"name": "<industry name>", "rationale": "<1 sentence>", "metrics": "<key numbers>"}}
  ],
  "top_avoid_industries": [
    {{"name": "<industry name>", "rationale": "<1 sentence>", "metrics": "<key numbers>"}}
  ],
  "disclaimer": "This is educational analysis only, not financial advice. Please consult a SEBI-registered advisor before making investment decisions."
}}
"""

# 24-hour in-process cache for sector analysis
_sector_analysis_cache: dict | None = None
_sector_analysis_ts:    float       = 0.0
_sector_analysis_lock   = threading.Lock()
_SECTOR_CACHE_TTL       = 24 * 3600


def run_sector_analysis(
    overview_rows: list[IndustryOverviewRow],
    force: bool = False,
) -> dict | None:
    """
    Call Gemini with the full 188-industry overview table and return structured
    sector rotation guidance (BUY/HOLD/AVOID per sector + top-5 buy/avoid industries).

    Result is cached for 24 hours in-process. Pass force=True to bypass.
    Returns None if the API key is not configured or Gemini fails.
    """
    global _sector_analysis_cache, _sector_analysis_ts

    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — skipping sector analysis")
        return None

    if not force:
        with _sector_analysis_lock:
            if _sector_analysis_cache and (time.time() - _sector_analysis_ts) < _SECTOR_CACHE_TTL:
                return _sector_analysis_cache

    if not overview_rows:
        return None

    # ── Build compact industry table for the prompt ───────────────────────────
    # Sort by sector code (L1) then by total_mktcap desc so highest-weight
    # industries appear first within each sector group.
    def _pct(v: float | None) -> str:
        return f"{v:+.0f}%" if v is not None else "—"

    def _pe(v: float | None) -> str:
        return f"{v:.0f}x" if v is not None else "—"

    def _cr(v: float | None) -> str:
        if v is None:
            return "—"
        if v >= 100_000:
            return f"₹{v/100_000:.1f}L Cr"
        if v >= 1_000:
            return f"₹{v/1_000:.0f}k Cr"
        return f"₹{v:.0f} Cr"

    # Limit to 188 rows but keep it terse — each row is ~80 chars
    lines = ["Industry | Cos | MCap | P/E | SalesGr | OPM | ROCE | 1YRet"]
    lines.append("-" * 70)
    for r in sorted(overview_rows, key=lambda x: x.name):
        lines.append(
            f"{r.name:<45} | {r.num_companies or '—':>4} | {_cr(r.total_mktcap):>10} "
            f"| {_pe(r.median_pe):>6} | {_pct(r.sales_growth):>7} "
            f"| {_pct(r.avg_opm):>6} | {_pct(r.avg_roce):>6} | {_pct(r.return_1y):>7}"
        )

    industry_table = "\n".join(lines)
    today = date.today().isoformat()

    user_msg = _SECTOR_USER_TEMPLATE.format(
        today=today,
        industry_table=industry_table,
    )

    # ── Call Gemini with enforced JSON schema ─────────────────────────────────
    _sector_schema = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "market_summary":       genai_types.Schema(type=genai_types.Type.STRING),
            "generated_at":         genai_types.Schema(type=genai_types.Type.STRING),
            "sectors":              genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "name":        genai_types.Schema(type=genai_types.Type.STRING),
                        "signal":      genai_types.Schema(type=genai_types.Type.STRING, enum=["BUY", "HOLD", "AVOID"]),
                        "rationale":   genai_types.Schema(type=genai_types.Type.STRING),
                        "key_metrics": genai_types.Schema(type=genai_types.Type.STRING),
                    },
                    required=["name", "signal", "rationale", "key_metrics"],
                ),
            ),
            "top_buy_industries":   genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "name":      genai_types.Schema(type=genai_types.Type.STRING),
                        "rationale": genai_types.Schema(type=genai_types.Type.STRING),
                        "metrics":   genai_types.Schema(type=genai_types.Type.STRING),
                    },
                    required=["name", "rationale", "metrics"],
                ),
            ),
            "top_avoid_industries": genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "name":      genai_types.Schema(type=genai_types.Type.STRING),
                        "rationale": genai_types.Schema(type=genai_types.Type.STRING),
                        "metrics":   genai_types.Schema(type=genai_types.Type.STRING),
                    },
                    required=["name", "rationale", "metrics"],
                ),
            ),
            "disclaimer":           genai_types.Schema(type=genai_types.Type.STRING),
        },
        required=["market_summary", "generated_at", "sectors", "top_buy_industries", "top_avoid_industries"],
    )

    client  = genai.Client(api_key=settings.gemini_api_key)
    gen_cfg = genai_types.GenerateContentConfig(
        system_instruction=_SECTOR_SYSTEM_PROMPT,
        max_output_tokens=2048,
        temperature=0.3,
        response_mime_type="application/json",
        response_schema=_sector_schema,
    )

    models_to_try = [settings.gemini_model]
    if settings.gemini_model_fallback and settings.gemini_model_fallback != settings.gemini_model:
        models_to_try.append(settings.gemini_model_fallback)

    result: dict | None = None
    for attempt_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=attempt_model,
                contents=user_msg,
                config=gen_cfg,
            )
            raw_text = (response.text or "").strip()
            if raw_text:
                import json as _json
                result = _json.loads(raw_text)
                logger.info(f"Gemini sector analysis OK using {attempt_model}")
                break
            logger.warning(f"Gemini returned empty sector analysis from {attempt_model}, trying fallback")
        except Exception as exc:
            err_str = str(exc)
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                logger.warning(f"Gemini {attempt_model} overloaded for sector analysis, trying fallback")
            else:
                logger.error(f"Gemini sector analysis failed ({attempt_model}): {exc}")
                return None

    if not result:
        logger.error("All Gemini models unavailable for sector analysis")
        return None

    # Normalise signal values
    for sec in result.get("sectors", []):
        sig = str(sec.get("signal", "HOLD")).upper()
        sec["signal"] = sig if sig in ("BUY", "HOLD", "AVOID") else "HOLD"
    for ind in result.get("top_buy_industries", []):
        ind["signal"] = "BUY"
    for ind in result.get("top_avoid_industries", []):
        ind["signal"] = "AVOID"

    result["cached_at"] = time.time()

    with _sector_analysis_lock:
        _sector_analysis_cache = result
        _sector_analysis_ts    = time.time()

    return result
