"""
AI Agent service.

Principle: the LLM interprets, it does not compute.
All indicators are computed deterministically and passed as structured
input. The LLM returns structured JSON which is stored in agent_analysis.

Public API
----------
  run_analysis(symbol, exchange, db)  →  AgentAnalysis (ORM row, not yet committed)
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

import anthropic
from loguru import logger
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import AgentAnalysis, AgentFeedback, RiskProfile
from backend.app.services.indicators import IndicatorSnapshot, compute_indicators

settings = get_settings()

# ── Prompt templates ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a careful, evidence-based market analyst assistant for Indian equities.
You interpret technical indicators and provide plain-language analysis.
You never give direct buy/sell instructions. Your output is always framed as
educational analysis with explicit caveats about uncertainty.
You respond ONLY with valid JSON matching the schema provided.
"""

_USER_TEMPLATE = """\
Analyse the following stock and return a JSON object.

## Stock
Symbol: {symbol}  |  Exchange: {exchange}

## Current Price & Recent Returns
Current price:         ₹{current_price}
1-day change:          {pct_change_1d}%
5-day change:          {pct_change_5d}%
30-day change:         {pct_change_30d}%

## Technical Indicators
RSI (14):              {rsi_14}
SMA-20:                ₹{sma_20}
SMA-50:                ₹{sma_50}
EMA-20:                ₹{ema_20}
Price vs SMA-20:       {price_vs_sma20_pct}%
Realized vol (30d ann): {realized_volatility_30d}%

## User Risk Profile
Time horizon:          {time_horizon}
Loss tolerance:        {loss_tolerance}
Experience level:      {experience_level}

## Past Signal Track Record (last 3 analyses on this symbol)
{feedback_digest}

## Response schema (return ONLY this JSON, no markdown, no extra text)
{{
  "summary": "<2-3 sentence plain-language trend summary>",
  "risk_flag": "<low|medium|high>",
  "caveats": "<1-2 sentences on key uncertainties or data limitations>",
  "disclaimer": "This is educational analysis only, not financial advice."
}}
"""

# ── Main function ─────────────────────────────────────────────────────────────

def run_analysis(symbol: str, exchange: str, db: Session) -> Optional[AgentAnalysis]:
    """
    Compute indicators, assemble prompt, call Claude, store result.
    Returns the unsaved AgentAnalysis ORM row (caller must db.add + db.commit).
    Returns None if the API key is not configured.
    """
    if not settings.claude_api_key:
        logger.warning("CLAUDE_API_KEY not set — skipping AI analysis")
        return None

    # ── 1. Compute indicators ─────────────────────────────────────────────────
    snap: IndicatorSnapshot = compute_indicators(symbol, exchange, db)

    # ── 2. Load risk profile ──────────────────────────────────────────────────
    risk = db.query(RiskProfile).first()
    risk_ctx = {
        "time_horizon": risk.time_horizon if risk else "medium",
        "loss_tolerance": risk.loss_tolerance if risk else "medium",
        "experience_level": risk.experience_level if risk else "intermediate",
    }

    # ── 3. Build feedback digest ──────────────────────────────────────────────
    feedback_digest = _build_feedback_digest(symbol, exchange, db)

    # ── 4. Build prompt ───────────────────────────────────────────────────────
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
        feedback_digest=feedback_digest,
        **risk_ctx,
    )

    # ── 5. Call Claude ────────────────────────────────────────────────────────
    try:
        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        message = client.messages.create(
            model=settings.claude_model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw_text = message.content[0].text.strip()
    except Exception as exc:
        logger.error(f"Claude API call failed for {symbol}: {exc}")
        return None

    # ── 6. Parse JSON response ────────────────────────────────────────────────
    try:
        structured = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning(f"Claude returned non-JSON for {symbol}, storing raw text")
        structured = {"summary": raw_text, "risk_flag": "medium", "caveats": "", "disclaimer": ""}

    risk_flag = structured.get("risk_flag", "medium")
    if risk_flag not in ("low", "medium", "high"):
        risk_flag = "medium"

    # ── 7. Build ORM row ──────────────────────────────────────────────────────
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
    """
    Summarise the last 3 completed analysis+feedback pairs for this symbol
    so the LLM can factor in its own track record.
    """
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
        feedback_rows = a.feedback
        if feedback_rows:
            fb = feedback_rows[-1]
            usefulness = (
                "flag was useful" if fb.was_flag_useful
                else "flag was not useful" if fb.was_flag_useful is False
                else "outcome pending"
            )
            lines.append(
                f"- {a.generated_at.date()}: risk_flag={a.risk_flag}, "
                f"outcome={_fmt(fb.outcome_pct_change)}% change, {usefulness}"
            )
        else:
            lines.append(
                f"- {a.generated_at.date()}: risk_flag={a.risk_flag}, no feedback yet"
            )

    return "\n".join(lines)


def _fmt(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
