"""
AI Agent service.

Principle: the LLM interprets, it does not compute.
All indicators and signals are computed deterministically in Python and passed
as structured input. The LLM returns structured JSON stored in agent_analysis.

Public API
----------
  run_analysis(symbol, exchange, db)  →  AgentAnalysis (ORM row, not yet committed)
"""
from __future__ import annotations

import json
import re as _re
from datetime import date, timedelta
from typing import Optional

from google import genai
from google.genai import types as genai_types
from loguru import logger
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import AgentAnalysis, AgentFeedback, RiskProfile
from backend.app.services.data_fetch import fetch_news
from backend.app.services.indicators import IndicatorSnapshot, compute_indicators

settings = get_settings()

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
  "summary": "<2-3 sentence plain-language trend summary incorporating indicators and news>",
  "recommendation": "<BUY|HOLD|SELL|AVOID>",
  "rationale": "<2-3 sentences explaining exactly which signals and news drove the recommendation>",
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

    # ── 1. Compute indicators + signals ──────────────────────────────────────
    snap: IndicatorSnapshot = compute_indicators(symbol, exchange, db)

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
        news_context=news_lines,
        feedback_digest=feedback_digest,
        **risk_ctx,
    )

    # ── 6. Call Gemini (primary model, fall back on 503/429 overload) ─────────
    client = genai.Client(api_key=settings.gemini_api_key)
    gen_cfg = genai_types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        max_output_tokens=1024,
        temperature=0.2,
    )

    models_to_try = [settings.gemini_model]
    if settings.gemini_model_fallback and settings.gemini_model_fallback != settings.gemini_model:
        models_to_try.append(settings.gemini_model_fallback)

    raw_text: str | None = None
    for attempt_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=attempt_model,
                contents=user_msg,
                config=gen_cfg,
            )
            raw_text = (response.text or "").strip()
            if raw_text:
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

    if not raw_text:
        logger.error(f"All Gemini models unavailable for {symbol}")
        return None

    # ── 7. Parse JSON response ────────────────────────────────────────────────
    clean = raw_text
    if "```" in clean:
        parts = clean.split("```")
        clean = parts[1].lstrip("json").strip() if len(parts) >= 3 else parts[1].strip()
    if clean.startswith("```"):
        clean = clean[3:].lstrip("json").strip()

    structured: dict | None = None
    try:
        structured = json.loads(clean)
    except json.JSONDecodeError:
        m = _re.search(r'\{.*\}', clean, _re.DOTALL)
        if m:
            try:
                structured = json.loads(m.group())
                logger.debug(f"Extracted JSON from surrounding text for {symbol}")
            except json.JSONDecodeError:
                pass

    if not structured:
        logger.error(f"Gemini returned unparseable response for {symbol}: {raw_text[:200]}")
        return None

    # Validate / normalise fields
    risk_flag = structured.get("risk_flag", "medium")
    if risk_flag not in ("low", "medium", "high"):
        risk_flag = "medium"

    recommendation = structured.get("recommendation", "HOLD").upper()
    if recommendation not in ("BUY", "HOLD", "SELL", "AVOID"):
        recommendation = "HOLD"
    structured["recommendation"] = recommendation

    # ── 8. Build ORM row ──────────────────────────────────────────────────────
    review_date = (date.today() + timedelta(days=settings.agent_feedback_days)).isoformat()
    analysis = AgentAnalysis(
        symbol=symbol,
        exchange=exchange,
        indicators_snapshot=snap.to_dict(),
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


def _fmt(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
